"""
=============================================================================
ORDER MANAGEMENT EXECUTION MATRICES: exeamspxy.py (ams)
Bridges raw data frame states to live automated order placement structures.
=============================================================================
"""
import logging
from datetime import datetime
from colorama import Fore, init

init(autoreset=True)
logger = logging.getLogger("exeavxpxy.strategy")

from syscnfgpxy import (
    SYSCNFGPXY_ENTRY_CUTOFF,
    SYSCNFGPXY_TIMEZONE,
    EXEAMSPXY_MAX_INVESTMENT,
    PXY_AVG_MODE,
    PXY_CAPACITY_MAX_LAYERS,
    EXEAMSPXY_ORDER_AMO,
    EXEAMSPXY_ORDER_EXCHANGE_SEGMENT,
    EXEAMSPXY_ORDER_PRICE,
    EXEAMSPXY_ORDER_PRODUCT,
    EXEAMSPXY_ORDER_TRANSACTION_TYPE,
    EXEAMSPXY_ORDER_TYPE,
    EXEAMSPXY_ORDER_VALIDITY,
)
from exeacgpxy import (
    safe_float, generate_pxy_tag, is_cooling, set_cooling, clear_cooling,
    print_pxy_trigger_dashboard
)
from sysdcinpxy import averaging_trigger_sides
from sysdcinpxy import averaging_order_response_accepted

def _newest_row(rows):
    """Newest lot by buy_time; falls back to the old behaviour if the column is unusable."""
    if 'buy_time' in rows.columns:
        try:
            return rows.sort_values('buy_time', kind='stable').iloc[-1]
        except Exception:
            pass
    return rows.iloc[-1]


def _order_ok(resp):
    """Same rule as exeexitpxy: a falsy reply or a broker error/failed reply is NOT a success."""
    return averaging_order_response_accepted(resp)


def _order_rejected(resp):
    """Return True only for an explicit broker rejection; unknown replies stay locked."""
    if not isinstance(resp, dict):
        return False
    status = str(resp.get("stat", "")).strip().lower()
    return status in {"not_ok", "failed", "error", "rejected"}


def execute_side_averaging_matrix(client, ce_rows, pe_rows, ce_lgt_val, pe_lgt_val,
                                  ce_dynamic_threshold, pe_dynamic_threshold, ce_lots, pe_lots,
                                  ce_aligned, pe_aligned, ce_investment, pe_investment,
                                  ce_opposite_signal=False, pe_opposite_signal=False,
                                  max_investment=EXEAMSPXY_MAX_INVESTMENT):
    """Executes network orders for System A when pullback boundaries are breached."""
    if datetime.now(SYSCNFGPXY_TIMEZONE).time() >= SYSCNFGPXY_ENTRY_CUTOFF:
        logger.warning("Averaging blocked: 15:14 IST hard buy cutoff")
        return
    ce_last_row = _newest_row(ce_rows) if not ce_rows.empty else None
    pe_last_row = _newest_row(pe_rows) if not pe_rows.empty else None
    ce_next_investment = (
        abs(int(safe_float(ce_last_row.get("qty", 0.0))))
        * max(0.0, safe_float(ce_last_row.get("sell_prc", 0.0)))
        if ce_last_row is not None else 0.0
    )
    pe_next_investment = (
        abs(int(safe_float(pe_last_row.get("qty", 0.0))))
        * max(0.0, safe_float(pe_last_row.get("sell_prc", 0.0)))
        if pe_last_row is not None else 0.0
    )
    # Capacity uses current sell-price worth, not the historical purchase cost.
    # Use the exact next order quantity/contract from the newest row.
    def side_worth(rows):
        return sum(
            max(0.0, safe_float(row.get("qty", 0)))
            * max(0.0, safe_float(row.get("sell_prc", 0)))
            for _, row in rows.iterrows()
        )

    ce_worth = side_worth(ce_rows)
    pe_worth = side_worth(pe_rows)
    # Count actual open NIFTY lots, not dataframe rows: broker positions may
    # consolidate several fills into one row. Reject malformed/partial lots.
    from syscnfgpxy import SYSCNFGPXY_NIFTY_LOT_SIZE

    def capacity_lots(rows):
        lot_size = SYSCNFGPXY_NIFTY_LOT_SIZE
        if not isinstance(lot_size, int) or isinstance(lot_size, bool) or lot_size <= 0:
            return None
        total_qty = 0
        for _, row in rows.iterrows():
            qty = safe_float(row.get("qty", 0))
            if not (qty > 0 and qty.is_integer()):
                return None
            total_qty += int(qty)
        if total_qty % lot_size:
            return None
        return total_qty // lot_size

    ce_open_lots = capacity_lots(ce_rows)
    pe_open_lots = capacity_lots(pe_rows)
    ce_order_qty = abs(int(safe_float(ce_last_row.get("qty", 0)))) if ce_last_row is not None else 0
    pe_order_qty = abs(int(safe_float(pe_last_row.get("qty", 0)))) if pe_last_row is not None else 0
    ce_next_lots = ce_order_qty // SYSCNFGPXY_NIFTY_LOT_SIZE if SYSCNFGPXY_NIFTY_LOT_SIZE > 0 and ce_order_qty % SYSCNFGPXY_NIFTY_LOT_SIZE == 0 else None
    pe_next_lots = pe_order_qty // SYSCNFGPXY_NIFTY_LOT_SIZE if SYSCNFGPXY_NIFTY_LOT_SIZE > 0 and pe_order_qty % SYSCNFGPXY_NIFTY_LOT_SIZE == 0 else None
    ce_capacity_ok = (
        ce_open_lots is not None and ce_next_lots is not None and ce_next_lots > 0
        and ce_open_lots + ce_next_lots <= PXY_CAPACITY_MAX_LAYERS
        and ce_last_row is not None and ce_next_investment > 0
        and ce_worth > 0 and pe_worth > 0
        and ce_worth < pe_worth
        and ce_worth + ce_next_investment <= pe_worth
    )
    pe_capacity_ok = (
        pe_open_lots is not None and pe_next_lots is not None and pe_next_lots > 0
        and pe_open_lots + pe_next_lots <= PXY_CAPACITY_MAX_LAYERS
        and pe_last_row is not None and pe_next_investment > 0
        and pe_worth > 0 and ce_worth > 0
        and pe_worth < ce_worth
        and pe_worth + pe_next_investment <= ce_worth
    )
    triggers = averaging_trigger_sides(
        avg_mode=PXY_AVG_MODE,
        ce_capacity_ok=ce_capacity_ok,
        pe_capacity_ok=pe_capacity_ok,
        ce_aligned=ce_aligned,
        pe_aligned=pe_aligned,
        ce_opposite_signal=ce_opposite_signal,
        pe_opposite_signal=pe_opposite_signal,
        ce_rows=len(ce_rows),
        pe_rows=len(pe_rows),
        ce_investment=ce_investment,
        pe_investment=pe_investment,
        ce_cooling=is_cooling("CE"),
        pe_cooling=is_cooling("PE"),
        ce_loss=ce_lgt_val,
        pe_loss=pe_lgt_val,
        ce_threshold=ce_dynamic_threshold,
        pe_threshold=pe_dynamic_threshold,
        max_investment=max_investment,
        ce_next_investment=ce_next_investment,
        pe_next_investment=pe_next_investment,
    )

    # 🟢 CALL OPTION (CE) SIDE LAYER GATEWAY
    if (
        ce_rows.shape[0] > 0
        and ce_investment + ce_next_investment > max_investment
    ):
        logger.info(
            "CE averaging blocked: projected investment %.2f exceeds value cap %.2f.",
            ce_investment + ce_next_investment,
            max_investment,
        )
    if triggers["CE"]:
        ce_symbol = ce_last_row['symbol']
        ce_qty = abs(int(safe_float(ce_last_row.get('qty', 0.0))))

        logger.info(f"⚖️ CE TRIGGERED: Metric Value ({ce_lgt_val}%) <= Threshold ({ce_dynamic_threshold}%).")
        try:
            new_tag = generate_pxy_tag()
            print_pxy_trigger_dashboard("CE", ce_symbol, ce_lgt_val, ce_dynamic_threshold, new_tag, ce_lots, pe_lots, "AUTO")
            params = {
                "exchange_segment": EXEAMSPXY_ORDER_EXCHANGE_SEGMENT,
                "product": EXEAMSPXY_ORDER_PRODUCT,
                "price": EXEAMSPXY_ORDER_PRICE,
                "order_type": EXEAMSPXY_ORDER_TYPE,
                "quantity": str(ce_qty), "trading_symbol": str(ce_symbol),
                "transaction_type": EXEAMSPXY_ORDER_TRANSACTION_TYPE,
                "validity": EXEAMSPXY_ORDER_VALIDITY,
                "amo": EXEAMSPXY_ORDER_AMO,
                "tag": new_tag
            }
            set_cooling("CE")      # stays BEFORE the send to prevent a duplicate buy
            if datetime.now(SYSCNFGPXY_TIMEZONE).time() >= SYSCNFGPXY_ENTRY_CUTOFF:
                logger.warning("Averaging order blocked by 15:14 IST hard cutoff")
                return
            resp = client.place_order(**params)
            if _order_ok(resp):
                print(f"{Fore.GREEN}✅ SUCCESS: CE Averaged. Tag: {new_tag}")
            else:
                print(f"{Fore.RED}❌ CE averaging order NOT confirmed: {resp}")
                if _order_rejected(resp):
                    clear_cooling("CE")
        except Exception as e:
            logger.error(f"CE Native placement tracking error: {e}", exc_info=True)

    # 🔴 PUT OPTION (PE) SIDE LAYER GATEWAY
    if (
        pe_rows.shape[0] > 0
        and pe_investment + pe_next_investment > max_investment
    ):
        logger.info(
            "PE averaging blocked: projected investment %.2f exceeds value cap %.2f.",
            pe_investment + pe_next_investment,
            max_investment,
        )
    if triggers["PE"]:
        pe_symbol = pe_last_row['symbol']
        pe_qty = abs(int(safe_float(pe_last_row.get('qty', 0.0))))

        logger.info(f"⚖️ PE TRIGGERED: Metric Value ({pe_lgt_val}%) <= Threshold ({pe_dynamic_threshold}%).")
        try:
            new_tag = generate_pxy_tag()
            print_pxy_trigger_dashboard("PE", pe_symbol, pe_lgt_val, pe_dynamic_threshold, new_tag, ce_lots, pe_lots, "AUTO")
            params = {
                "exchange_segment": EXEAMSPXY_ORDER_EXCHANGE_SEGMENT,
                "product": EXEAMSPXY_ORDER_PRODUCT,
                "price": EXEAMSPXY_ORDER_PRICE,
                "order_type": EXEAMSPXY_ORDER_TYPE,
                "quantity": str(pe_qty), "trading_symbol": str(pe_symbol),
                "transaction_type": EXEAMSPXY_ORDER_TRANSACTION_TYPE,
                "validity": EXEAMSPXY_ORDER_VALIDITY,
                "amo": EXEAMSPXY_ORDER_AMO,
                "tag": new_tag
            }
            set_cooling("PE")      # stays BEFORE the send to prevent a duplicate buy
            if datetime.now(SYSCNFGPXY_TIMEZONE).time() >= SYSCNFGPXY_ENTRY_CUTOFF:
                logger.warning("Averaging order blocked by 15:14 IST hard cutoff")
                return
            resp = client.place_order(**params)
            if _order_ok(resp):
                print(f"{Fore.GREEN}✅ SUCCESS: PE Averaged. Tag: {new_tag}")
            else:
                print(f"{Fore.RED}❌ PE averaging order NOT confirmed: {resp}")
                if _order_rejected(resp):
                    clear_cooling("PE")
        except Exception as e:
            logger.error(f"PE Native placement tracking error: {e}", exc_info=True)
