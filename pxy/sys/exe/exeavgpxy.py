# =============================================================================
# MAIN MODULE: exeavgpxy.py - PART 1
# UNIFIED STRUCTURAL DATA AGGREGATION & TELEMETRY ENGINE
# =============================================================================
import re
import logging
from datetime import datetime
from colorama import Fore, Style

# Import the newly isolated threshold calculation engine
from exeagtpxy import exeagtpxy

# Direct module dependency linking to inherit essential infrastructure variables
from exehvgpxy import (
    REBUY_ENABLED, MAX_LAYERS, IST, MARKET_START, MARKET_END,
    safe_float, generate_pxy_tag, is_cooling, set_cooling, get_loss,
    print_pxy_trigger_dashboard
)
from run.runpchkpxy import get_position_summary

# Configure localized robust module logger
logger = logging.getLogger("exeavgpxy")


def print_telemetry_dashboard(p):
    """Constructs the visual geometric dashboard panel layout within a strict 40-char width."""
    if not p:
        return
    ce_agt = int(round(p["ce_dynamic_threshold"]))
    pe_agt = int(round(p["pe_dynamic_threshold"]))
    
    ce_target_crossed = p["ce_avg_profit"] >= p["ce_tgt"] if p["ce_lots"] > 0 else False
    pe_target_crossed = p["pe_avg_profit"] >= p["pe_tgt"] if p["pe_lots"] > 0 else False

    # Switched from variable-length Emojis to clean 2-char ASCII states to protect space alignment
    ce_sts = "OK" if ce_target_crossed else "NO"
    pe_sts = "OK" if pe_target_crossed else "NO"
    
    P_WIDTH = 40 
    print("\n" + Fore.CYAN + "=" * P_WIDTH)
    print(Fore.CYAN + " OPT  LOT   LGT   AGT  STS  TGT      PNL")
    print(Fore.CYAN + "-" * P_WIDTH)
    
    # Grid Layout Grid Blueprint (Exact 40 characters):
    # OPT[3] + ' '[1] + LOT[4] + ' '[1] + LGT[5] + ' '[1] + AGT[5] + ' '[1] + STS[4] + ' '[1] + TGT[4] + ' '[1] + PNL[9] = 40 chars
    ce_lgt = int(round(p["ce_lgt"]))
    ce_pnl_val = int(round(p["ce_pnl"]))
    ce_pnl_color = Fore.CYAN + Style.BRIGHT if ce_target_crossed else (Fore.GREEN if ce_pnl_val >= 0 else Fore.RED)
    print(Fore.WHITE + f"{'CE':>4} {p['ce_lots']:>4} {ce_lgt:>5} {ce_agt:>5} {ce_sts:>4} {p['ce_tgt']:>4} " + ce_pnl_color + f"{ce_pnl_val:>8}" + Style.RESET_ALL)
    
    pe_lgt = int(round(p["pe_lgt"]))
    pe_pnl_val = int(round(p["pe_pnl"]))
    pe_pnl_color = Fore.CYAN + Style.BRIGHT if pe_target_crossed else (Fore.GREEN if pe_pnl_val >= 0 else Fore.RED)
    print(Fore.WHITE + f"{'PE':>4} {p['pe_lots']:>4} {pe_lgt:>5} {pe_agt:>5} {pe_sts:>4} {p['pe_tgt']:>4} " + pe_pnl_color + f"{pe_pnl_val:>8}" + Style.RESET_ALL)
    print(Fore.CYAN + "-" * P_WIDTH)

    ce_weight_int = int(round(p["ce_investment"]))
    pe_weight_int = int(round(p["pe_investment"]))
    left_label = f"{ce_weight_int}"
    right_label = f"{pe_weight_int}"
    
    track_slots = P_WIDTH - len(left_label) - len(right_label) - 6
    total_weight = p["ce_investment"] + p["pe_investment"]
    ce_ratio = p["ce_investment"] / total_weight if total_weight > 0 else 0.5
    
    left_dashes_count = max(0, min(track_slots, int(round(ce_ratio * track_slots))))
    right_dashes_count = max(0, track_slots - left_dashes_count)
    
    print("  " + Fore.GREEN + left_label + Fore.GREEN + ("━" * left_dashes_count) + Fore.WHITE + "⚖️" + Fore.RED + ("━" * right_dashes_count) + Fore.RED + right_label)
    print(Fore.CYAN + "=" * P_WIDTH + "\n")


# =============================================================================
# MAIN MODULE: exeavgpxy.py - PART 2
# DATA PARSING ENGINE & REAL-TIME RISK METRIC DISPATCHER
# =============================================================================

def handle_side_averaging(client, df): 
    """Executes safe threshold-based automated averaging loops for derivative positions."""
    if df is None or df.empty: 
        return 
        
    now = datetime.now(IST).time() 
    if not REBUY_ENABLED or not (MARKET_START <= now <= MARKET_END): 
        return 

    working_df = df.copy()
    working_df['side'] = working_df['symbol'].astype(str).str[-2:].str.upper() 
    
    working_df['row_invested'] = working_df['qty'].apply(safe_float) * (
        (working_df['sell_prc'].apply(safe_float) + working_df['sell_prc'].apply(safe_float)) / 2.0
    )
    
    if 'pnl' in working_df.columns:
        working_df['row_pnl'] = working_df['pnl'].apply(safe_float)
    else:
        working_df['row_pnl'] = 0.0

    pos_raw = str(get_position_summary(client)).upper().replace(" ", "").strip()
    ce_match = re.search(r'(\d+)CE', pos_raw)
    pe_match = re.search(r'(\d+)PE', pos_raw)
    
    ce_lots = int(ce_match.group(1)) if ce_match else 0
    pe_lots = int(pe_match.group(1)) if pe_match else 0  
    
    ce_rows = working_df[working_df['side'] == 'CE']
    pe_rows = working_df[working_df['side'] == 'PE']
    
    if not ce_rows.empty:
        ce_total_cost = (ce_rows['qty'].apply(safe_float) * ce_rows['buy_prc'].apply(safe_float)).sum()
        ce_total_value = (ce_rows['qty'].apply(safe_float) * ce_rows['sell_prc'].apply(safe_float)).sum()
        ce_overall_pnl_pct = ((ce_total_value - ce_total_cost) / ce_total_cost) * 100 if ce_total_cost > 0 else 0.0
    else:
        ce_overall_pnl_pct = 0.0

    if not pe_rows.empty:
        pe_total_cost = (pe_rows['qty'].apply(safe_float) * pe_rows['buy_prc'].apply(safe_float)).sum()
        pe_total_value = (pe_rows['qty'].apply(safe_float) * pe_rows['sell_prc'].apply(safe_float)).sum()
        pe_overall_pnl_pct = ((pe_total_value - pe_total_cost) / pe_total_cost) * 100 if pe_total_cost > 0 else 0.0
    else:
        pe_overall_pnl_pct = 0.0

    ce_avg_profit = ce_overall_pnl_pct if ce_overall_pnl_pct > 0 else 0.0
    pe_avg_profit = pe_overall_pnl_pct if pe_overall_pnl_pct > 0 else 0.0

    ce_investment = float(ce_rows['row_invested'].sum()) if not ce_rows.empty else 0.0
    pe_investment = float(pe_rows['row_invested'].sum()) if not pe_rows.empty else 0.0
    
    ce_invst_factor = ce_investment / pe_investment if (ce_investment > 0 and pe_investment > 0) else 1.0
    pe_invst_factor = pe_investment / ce_investment if (ce_investment > 0 and pe_investment > 0) else 1.0
    
    ce_pnl = float(ce_rows['row_pnl'].sum()) if not ce_rows.empty else 0.0
    pe_pnl = float(pe_rows['row_pnl'].sum()) if not pe_rows.empty else 0.0
    
    latest_row = working_df.iloc[-1]
    ce_power = safe_float(latest_row.get("ce_power") or latest_row.get("ce_p", 1.0))
    ce_depth = safe_float(latest_row.get("hkin_ce_depth") or latest_row.get("ce_d", 1.0))
    pe_power = safe_float(latest_row.get("pe_power") or latest_row.get("pe_p", 1.0))
    pe_depth = safe_float(latest_row.get("hkin_pe_depth") or latest_row.get("pe_d", 1.0))
    
    ce_matrix_self = max(ce_depth, ce_power)
    pe_matrix_self = max(pe_depth, pe_power)
    
    atr = safe_float(working_df['atr'].iloc[-1]) if 'atr' in working_df.columns and not working_df.empty else 0.0    
    ce_tgt = int(round(((atr / ce_lots) * ce_matrix_self))) if ce_lots > 0 else 0
    pe_tgt = int(round(((atr / pe_lots) * pe_matrix_self))) if pe_lots > 0 else 0

    # Execute computation using imported function
    ce_dynamic_threshold, pe_dynamic_threshold = exeagtpxy(atr, ce_invst_factor, pe_invst_factor)

    # Extract absolute native loss percentages from positions safely for visual transmission
    ce_lgt_val = get_loss(ce_rows.iloc[-1]) if not ce_rows.empty else 0.0
    pe_lgt_val = get_loss(pe_rows.iloc[-1]) if not pe_rows.empty else 0.0

    p_packet = {
        "ce_lots": ce_lots, "pe_lots": pe_lots, "ce_tgt": ce_tgt, "pe_tgt": pe_tgt, 
        "ce_pnl": ce_pnl, "pe_pnl": pe_pnl, "ce_avg_profit": ce_avg_profit, "pe_avg_profit": pe_avg_profit,
        "ce_investment": ce_investment, "pe_investment": pe_investment,
        "ce_dynamic_threshold": ce_dynamic_threshold, "pe_dynamic_threshold": pe_dynamic_threshold,
        "ce_lgt": ce_lgt_val, "pe_lgt": pe_lgt_val
    }

    print_telemetry_dashboard(p_packet)
    # -------------------------------------------------------------------------
    # [PART 2: ZERO-LOOP PURE DYNAMIC THRESHOLD EXECUTION MATRIX]
    # -------------------------------------------------------------------------
    
    # -------------------------------------------------------------------------
    # 🟢 CALL OPTION (CE) SAFE DIRECT THRESHOLD TRACKER
    # -------------------------------------------------------------------------
    if not ce_rows.empty and not is_cooling("CE") and len(ce_rows) < (MAX_LAYERS + 1):
        ce_last_row = ce_rows.iloc[-1]
        ce_symbol = ce_last_row['symbol']
        ce_qty = abs(int(safe_float(ce_last_row.get('qty', 0.0))))
        ce_final_loss = get_loss(ce_last_row)
        
        # ⚖️ Signed Negative Math: True when final loss drops below threshold boundary (e.g., -30 <= -18)
        if ce_final_loss <= ce_dynamic_threshold:
            logger.info(f"⚖️ CE TRIGGERED: Loss ({ce_final_loss}%) <= Threshold ({ce_dynamic_threshold}%).")
            try:
                new_tag = generate_pxy_tag()
                print_pxy_trigger_dashboard("CE", ce_symbol, ce_final_loss, ce_dynamic_threshold, new_tag, ce_lots, pe_lots, "AUTO")
                params = {
                    "exchange_segment": "nse_fo", "product": "NRML", "price": "0", "order_type": "MKT", 
                    "quantity": str(ce_qty), "trading_symbol": str(ce_symbol), "transaction_type": "B", 
                    "validity": "DAY", "amo": "NO", "tag": new_tag
                }
                # Lock script processing loop instantly before dispatching network request
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
        pe_final_loss = get_loss(pe_last_row)
        
        # ⚖️ Signed Negative Math: True when final loss drops below threshold boundary (e.g., -30 <= -18)
        if pe_final_loss <= pe_dynamic_threshold:
            logger.info(f"⚖️ PE TRIGGERED: Loss ({pe_final_loss}%) <= Threshold ({pe_dynamic_threshold}%).")
            try:
                new_tag = generate_pxy_tag()
                print_pxy_trigger_dashboard("PE", pe_symbol, pe_final_loss, pe_dynamic_threshold, new_tag, ce_lots, pe_lots, "AUTO")
                params = {
                    "exchange_segment": "nse_fo", "product": "NRML", "price": "0", "order_type": "MKT", 
                    "quantity": str(pe_qty), "trading_symbol": str(pe_symbol), "transaction_type": "B", 
                    "validity": "DAY", "amo": "NO", "tag": new_tag
                }
                # Lock script processing loop instantly before dispatching network request
                set_cooling("PE")
                if client.place_order(**params):
                    print(f"{Fore.GREEN}✅ SUCCESS: PE Averaged. Tag: {new_tag}")
            except Exception as e:
                logger.error(f"PE Native placement tracking error: {e}", exc_info=True)
