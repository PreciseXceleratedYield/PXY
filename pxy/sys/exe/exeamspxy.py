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
    if isinstance(resp, dict):
        stat = str(resp.get('stat', '')).lower()
        err = str(resp.get('errMsg', '')).lower()
        if "failed" in stat or "error" in err or "error" in stat:
            return False
    return bool(resp)


def execute_side_averaging_matrix(client, ce_rows, pe_rows, ce_lgt_val, pe_lgt_val,
                                  ce_dynamic_threshold, pe_dynamic_threshold, ce_lots, pe_lots,
                                  ce_aligned, pe_aligned):
    """Executes network orders for System A when pullback boundaries are breached."""
    
    # 🟢 CALL OPTION (CE) SIDE LAYER GATEWAY
    if ce_aligned and not ce_rows.empty and not is_cooling("CE") and len(ce_rows) < (MAX_LAYERS + 1):
        ce_last_row = _newest_row(ce_rows)
        ce_symbol = ce_last_row['symbol']
        ce_qty = abs(int(safe_float(ce_last_row.get('qty', 0.0))))

        if ce_lgt_val <= ce_dynamic_threshold:
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
    if pe_aligned and not pe_rows.empty and not is_cooling("PE") and len(pe_rows) < (MAX_LAYERS + 1):
        pe_last_row = _newest_row(pe_rows)
        pe_symbol = pe_last_row['symbol']
        pe_qty = abs(int(safe_float(pe_last_row.get('qty', 0.0))))

        if pe_lgt_val <= pe_dynamic_threshold:
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
