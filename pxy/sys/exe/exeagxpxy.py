# =============================================================================
# EXECUTOR MODULE: exeagxpxy.py
# DECOUPLED SAFE DIRECT THRESHOLD TRACKER & PLACEMENT ENGINE
# =============================================================================
import logging
from colorama import Fore

# Inherit tracking ecosystem components safely from master matrix configuration
from exehvgpxy import (
    MAX_LAYERS, safe_float, generate_pxy_tag, is_cooling, set_cooling,
    print_pxy_trigger_dashboard
)

logger = logging.getLogger("exeavgpxy.executor")


def execute_side_averaging_matrix(client, ce_rows, pe_rows, ce_lgt_val, pe_lgt_val, 
                                  ce_dynamic_threshold, pe_dynamic_threshold, ce_lots, pe_lots):
    """Handles deep-level active order execution tracking via raw network placement hooks."""
    
    # -------------------------------------------------------------------------
    # 🟢 CALL OPTION (CE) SAFE DIRECT THRESHOLD TRACKER
    # -------------------------------------------------------------------------
    if not ce_rows.empty and not is_cooling("CE") and len(ce_rows) < (MAX_LAYERS + 1):
        ce_last_row = ce_rows.iloc[-1]
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
                set_cooling("CE")
                if client.place_order(**params):
                    print(f"{Fore.GREEN}✅ SUCCESS: CE Averaged. Tag: {new_tag}")
            except Exception as e:
                logger.error(f"CE Native placement tracking error: {e}", exc_info=True)

    # -------------------------------------------------------------------------
    # 🔴 PUT OPTION (PE) SAFE DIRECT THRESHOLD TRACKER
    # -------------------------------------------------------------------------
    if not pe_rows.empty and not is_cooling("PE") and len(pe_rows) < (MAX_LAYERS + 1):
        pe_last_row = pe_rows.iloc[-1]
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
                set_cooling("PE")
                if client.place_order(**params):
                    print(f"{Fore.GREEN}✅ SUCCESS: PE Averaged. Tag: {new_tag}")
            except Exception as e:
                logger.error(f"PE Native placement tracking error: {e}", exc_info=True)
