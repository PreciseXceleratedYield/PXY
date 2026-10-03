"""
=============================================================================
ORDER MANAGEMENT EXECUTION MATRICES: exeamspxy.py (ams)
Bridges raw data frame states to live automated order placement structures.
=============================================================================
"""
import logging
from colorama import Fore, init

init(autoreset=True)
logger = logging.getLogger("exeavxpxy.strategy")

from exeacgpxy import (
    MAX_LAYERS, safe_float, generate_pxy_tag, is_cooling, set_cooling,
    print_pxy_trigger_dashboard
)
from sysdecisionpxy import averaging_trigger_sides
from sysdecisionpxy import averaging_order_response_accepted

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


def execute_side_averaging_matrix(client, ce_rows, pe_rows, ce_lgt_val, pe_lgt_val,
                                  ce_dynamic_threshold, pe_dynamic_threshold, ce_lots, pe_lots,
                                  ce_aligned, pe_aligned):
    """Executes network orders for System A when pullback boundaries are breached."""
    triggers = averaging_trigger_sides(
        ce_aligned=ce_aligned,
        pe_aligned=pe_aligned,
        ce_rows=len(ce_rows),
        pe_rows=len(pe_rows),
        ce_cooling=is_cooling("CE"),
        pe_cooling=is_cooling("PE"),
        ce_loss=ce_lgt_val,
        pe_loss=pe_lgt_val,
        ce_threshold=ce_dynamic_threshold,
        pe_threshold=pe_dynamic_threshold,
        max_layers=MAX_LAYERS,
    )

    # 🟢 CALL OPTION (CE) SIDE LAYER GATEWAY
    if triggers["CE"]:
        ce_last_row = _newest_row(ce_rows)
        ce_symbol = ce_last_row['symbol']
        ce_qty = abs(int(safe_float(ce_last_row.get('qty', 0.0))))

        logger.info(f"⚖️ CE TRIGGERED: Metric Value ({ce_lgt_val}%) <= Threshold ({ce_dynamic_threshold}%).")
        try:
            new_tag = generate_pxy_tag()
            print_pxy_trigger_dashboard("CE", ce_symbol, ce_lgt_val, ce_dynamic_threshold, new_tag, ce_lots, pe_lots, "AUTO")
            params = {
                "exchange_segment": "nse_fo", "product": "NRML", "price": "0", "order_type": "MKT",
                "quantity": str(ce_qty), "trading_symbol": str(ce_symbol), "transaction_type": "B",
                "validity": "DAY", "amo": "NO", "tag": new_tag
            }
            set_cooling("CE")      # stays BEFORE the send: a duplicate buy is worse than a 30 s wait
            resp = client.place_order(**params)
            if _order_ok(resp):
                print(f"{Fore.GREEN}✅ SUCCESS: CE Averaged. Tag: {new_tag}")
            else:
                print(f"{Fore.RED}❌ CE averaging order NOT confirmed: {resp}")
        except Exception as e:
            logger.error(f"CE Native placement tracking error: {e}", exc_info=True)

    # 🔴 PUT OPTION (PE) SIDE LAYER GATEWAY
    if triggers["PE"]:
        pe_last_row = _newest_row(pe_rows)
        pe_symbol = pe_last_row['symbol']
        pe_qty = abs(int(safe_float(pe_last_row.get('qty', 0.0))))

        logger.info(f"⚖️ PE TRIGGERED: Metric Value ({pe_lgt_val}%) <= Threshold ({pe_dynamic_threshold}%).")
        try:
            new_tag = generate_pxy_tag()
            print_pxy_trigger_dashboard("PE", pe_symbol, pe_lgt_val, pe_dynamic_threshold, new_tag, ce_lots, pe_lots, "AUTO")
            params = {
                "exchange_segment": "nse_fo", "product": "NRML", "price": "0", "order_type": "MKT",
                "quantity": str(pe_qty), "trading_symbol": str(pe_symbol), "transaction_type": "B",
                "validity": "DAY", "amo": "NO", "tag": new_tag
            }
            set_cooling("PE")      # stays BEFORE the send: a duplicate buy is worse than a 30 s wait
            resp = client.place_order(**params)
            if _order_ok(resp):
                print(f"{Fore.GREEN}✅ SUCCESS: PE Averaged. Tag: {new_tag}")
            else:
                print(f"{Fore.RED}❌ PE averaging order NOT confirmed: {resp}")
        except Exception as e:
            logger.error(f"PE Native placement tracking error: {e}", exc_info=True)
