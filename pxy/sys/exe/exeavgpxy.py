# =============================================================================
# MAIN MODULE: exeavgpxy.py [PART 1: DATA PARSERS & TELEMETRY STREAM PANEL]
# =============================================================================
import re
import os
import logging
import subprocess
from datetime import datetime
from colorama import Fore, Style, init

# Direct module dependency linking to inherit all variables from the helper script
from exehvgpxy import (
    REBUY_ENABLED, MAX_LAYERS, IST, MARKET_START, MARKET_END, 
    pxysqrce, pxysqrpe, safe_float, generate_pxy_tag, is_cooling, 
    set_cooling, get_loss, print_pxy_trigger_dashboard
)
from run.runpchkpxy import get_position_summary

# Configure localized robust module logger
logger = logging.getLogger("exeavgpxy")
init(autoreset=True)

def handle_side_averaging(client, df): 
    """
    Executes automated downward multi-layer directional matrix averaging loops
    for derivative positions based on rule matrices and structural exposure.
    """
    if df is None or df.empty: 
        return 
        
    now = datetime.now(IST).time() 
    if not REBUY_ENABLED or not (MARKET_START <= now <= MARKET_END): 
        return 

    # =============================================================================
    # PART 5: CORE POSITION COMPILATION, DATA PARSERS & MATRIX RESOLUTIONS
    # =============================================================================
    # Deep copy to fully isolate operations and prevent setting-with-copy warnings
    working_df = df.copy()
    
    # Safe standardized execution for underlying option contract side mapping
    working_df['side'] = working_df['symbol'].astype(str).str[-2:].str.upper() 
    working_df['row_invested'] = working_df['qty'].apply(safe_float) * (working_df['sell_prc'].apply(safe_float))
    
    # Shield against missing pnl column series failure
    if 'pnl' in working_df.columns:
        working_df['row_pnl'] = working_df['pnl'].apply(safe_float)
    else:
        working_df['row_pnl'] = 0.0

    # Compile explicit state summaries from position snapshots
    pos_raw = str(get_position_summary(client)).upper().replace(" ", "").strip()
    
    ce_match = re.search(r'(\d+)CE', pos_raw)
    pe_match = re.search(r'(\d+)PE', pos_raw)
    
    ce_lots = int(ce_match.group(1)) if ce_match else 0
    pe_lots = int(pe_match.group(1)) if pe_match else 0  
    
    # Aggregate dimensional matrix groupings
    ce_rows = working_df[working_df['side'] == 'CE']
    pe_rows = working_df[working_df['side'] == 'PE']
    
    # 💰 MATHEMATICALLY ROBUST OVERALL PERFORMANCE PERCENTAGE MATRIX
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

    # Convert overall performance matrix to a positive "loss value" to safely hit targets
    ce_avg_loss = -ce_overall_pnl_pct if ce_overall_pnl_pct < 0 else 0.0
    pe_avg_loss = -pe_overall_pnl_pct if pe_overall_pnl_pct < 0 else 0.0

    # Structural exposure factor resolutions
    ce_investment = float(ce_rows['row_invested'].sum()) if not ce_rows.empty else 0.0
    pe_investment = float(pe_rows['row_invested'].sum()) if not pe_rows.empty else 0.0
    
    ce_factor = ce_investment / pe_investment if (ce_investment > 0 and pe_investment > 0) else 1.0
    pe_factor = pe_investment / ce_investment if (ce_investment > 0 and pe_investment > 0) else 1.0

    ce_pnl = float(ce_rows['row_pnl'].sum())
    pe_pnl = float(pe_rows['row_pnl'].sum())
    
    ce_last = ce_rows.iloc[-1] if not ce_rows.empty else {}
    pe_last = pe_rows.iloc[-1] if not pe_rows.empty else {}
    
    # ⚡ SAFE DUAL-KEY EXTRACTION STRATEGY
    ce_power = safe_float(ce_last.get("ce_power") or ce_last.get("ce_p", 1.0))
    ce_depth = safe_float(ce_last.get("hkin_ce_depth") or ce_last.get("ce_d", 1.0))
    
    pe_power = safe_float(pe_last.get("pe_power") or pe_last.get("pe_p", 1.0))
    pe_depth = safe_float(pe_last.get("hkin_pe_depth") or pe_last.get("pe_d", 1.0))
    
    ce_matrix_self = max(ce_depth, ce_power)
    pe_matrix_self = max(pe_depth, pe_power)
    
    # 🎯 VOLATILITY-UNIFIED TARGET FORMULA RESOLUTION: GLOBAL ATR ENGINE
    atr = safe_float(working_df['atr'].iloc[0]) if 'atr' in working_df.columns and not working_df.empty else 0.0
    
    ce_tgt = int(round(((atr / ce_lots) * ce_matrix_self))) if ce_lots > 0 else 0
    pe_tgt = int(round(((atr / pe_lots) * pe_matrix_self))) if pe_lots > 0 else 0

    # Extract entry fields directly from the side snapshots since they are identical across rows
    ce_avg_entry = str(ce_last.get("entry", "NONE")).upper().strip() if not ce_rows.empty else "NONE"
    pe_avg_entry = str(pe_last.get("entry", "NONE")).upper().strip() if not pe_rows.empty else "NONE"

    # --- ZERO-DIVISION SHIELDED LOTS FACTOR ENGINE ---
    ce_lots_factor = (ce_lots + 1) / (pe_lots + 1) if pe_lots >= 0 else 1.0
    pe_lots_factor = (pe_lots + 1) / (ce_lots + 1) if ce_lots >= 0 else 1.0

    # --- PRE-CALCULATE DYNAMIC THRESHOLDS MULTIPLIED ACROSS THE WHOLE THING ---
    ce_base_drawdown_limit = -atr * 1.4
    if "MBUY" in ce_avg_entry:
        ce_dynamic_threshold = (
            ce_base_drawdown_limit * ce_factor * ce_lots_factor
        ) * 1.4
    else:
        ce_dynamic_threshold = ce_base_drawdown_limit * 14

    pe_base_drawdown_limit = -atr * 1.4
    if "MSELL" in pe_avg_entry:
        pe_dynamic_threshold = (
            pe_base_drawdown_limit * pe_factor * pe_lots_factor
        ) * 1.4
    else:
        pe_dynamic_threshold = pe_base_drawdown_limit * 14

    # 📊 VOLATILITY-UNIFIED AGT RESOLUTION LINKED TO COMBINED DYNAMIC THRESHOLDS
    ce_agt = int(round(ce_dynamic_threshold))
    pe_agt = int(round(pe_dynamic_threshold))
    
    # 🎯 MONITOR TARGET PERCENTAGE CROSSINGS (ACTUAL OVERALL LOSS >= POSITIVE TGT %)
    ce_target_crossed = ce_avg_loss >= ce_tgt if ce_lots > 0 else False
    pe_target_crossed = pe_avg_loss >= pe_tgt if pe_lots > 0 else False

    ce_sts = "✔️" if ce_target_crossed else "❌"
    pe_sts = "✔️" if pe_target_crossed else "❌"

    if ce_target_crossed and "MBUY" in ce_avg_entry:
        pass  # Synchronized execution hooks

    if pe_target_crossed and "MSELL" in pe_avg_entry:
        pass  # Synchronized execution hooks

    # =============================================================================
    # MAIN MODULE: exeavgpxy.py [PART 2: TELEMETRY & INLINE ORDER PLACEMENT ENGINE]
    # =============================================================================
    # =============================================================================
    # PART 6: TELEMETRY STREAM PANEL GRAPHICS & BALANCED GEOMETRIC RATIO BAR
    # =============================================================================
    P_WIDTH = 40  # Preserved standard size width
    
    print("\n" + Fore.CYAN + "=" * P_WIDTH)
    print(Fore.CYAN + "OPT LOT PNL AGT TGT STS")
    print(Fore.CYAN + "-" * P_WIDTH)
    
    ce_pnl_val = int(round(ce_pnl))
    ce_pnl_color = Fore.CYAN + Style.BRIGHT if ce_target_crossed else (Fore.GREEN if ce_pnl_val >= 0 else Fore.RED)
    print(Fore.WHITE + f" CE  {ce_lots:>2} " + ce_pnl_color + f"{ce_pnl_val:>7}" + Style.RESET_ALL + f" {ce_agt:>4} {ce_tgt:>4} {ce_sts}")
    
    pe_pnl_val = int(round(pe_pnl))
    pe_pnl_color = Fore.CYAN + Style.BRIGHT if pe_target_crossed else (Fore.GREEN if pe_pnl_val >= 0 else Fore.RED)
    print(Fore.WHITE + f" PE  {pe_lots:>2} " + pe_pnl_color + f"{pe_pnl_val:>7}" + Style.RESET_ALL + f" {pe_agt:>4} {pe_tgt:>4} {pe_sts}")
    print(Fore.CYAN + "-" * P_WIDTH)

    # --- DRAW THE DYNAMIC GEOMETRIC BALANCE BAR ---
    ce_weight_int = int(round(ce_investment))
    pe_weight_int = int(round(pe_investment))
    
    left_label = f"{ce_weight_int}"
    right_label = f"{pe_weight_int}"
    
    track_slots = P_WIDTH - len(left_label) - len(right_label) - 6
    total_weight = ce_investment + pe_investment
    ce_ratio = ce_investment / total_weight if total_weight > 0 else 0.5
    
    left_dashes_count = max(0, min(track_slots, int(round(ce_ratio * track_slots))))
    right_dashes_count = max(0, track_slots - left_dashes_count)
    
    left_dash_track = "━" * left_dashes_count
    right_dash_track = "━" * right_dashes_count
    
    print("  " + Fore.GREEN + left_label + Fore.GREEN + left_dash_track + Fore.WHITE + "⚖️" + Fore.RED + right_dash_track + Fore.RED + right_label)
    print(Fore.CYAN + "=" * P_WIDTH + "\n")

    # =============================================================================
    # PART 7: NATIVE INLINE MULTI-LAYER DOWNWARD DIRECTIONAL MATRIX AVERAGING ENGINE
    # =============================================================================
    for side in ['CE', 'PE']:
        side_df = ce_rows if side == 'CE' else pe_rows
        if side_df.empty:
            continue
            
        last_row = side_df.iloc[-1]
        active_exit = ce_avg_entry if side == 'CE' else pe_avg_entry
    
        all_positions_crossed_threshold = True
        last_calculated_threshold = 0.0
        
        # Link loops instantly to the identical combined factor thresholds
        if side == 'CE':
            dynamic_threshold = ce_dynamic_threshold
        else: # side == 'PE'
            dynamic_threshold = pe_dynamic_threshold
                
        last_calculated_threshold = dynamic_threshold
        
        # --- SCAN INDIVIDUAL POSITION ROWS ---
        for _, row in side_df.iterrows():
            pos_loss = get_loss(row)
            
            # 🎯 ORIGINAL NEGATIVE LOGIC COMPLETELY PRESERVED AS VERIFIED CORRECT
            if not (dynamic_threshold > pos_loss):
                all_positions_crossed_threshold = False
                break
                
        # --- PLACE SYSTEM AVERAGING ORDER DIRECTLY VIA CLIENT ---
        if all_positions_crossed_threshold and len(side_df) < (MAX_LAYERS + 1):
            if not is_cooling(side):
                symbol = last_row['symbol']
                qty = abs(int(safe_float(last_row.get('qty', 0.0))))
                new_tag = generate_pxy_tag()
                final_loss = get_loss(last_row)
                
                # Render deployment state trace directly to the stream panel
                print_pxy_trigger_dashboard(
                    side, symbol, final_loss, last_calculated_threshold, new_tag, 
                    ce_lots, pe_lots, active_exit
                )
                
                try:
                    # Construct optimized parameters dictionary mapped for standard F&O parameters
                    params = {
                        "exchange_segment": "nse_fo", 
                        "product": "NRML", 
                        "price": "0",
                        "order_type": "MKT", 
                        "quantity": str(qty), 
                        "trading_symbol": str(symbol),
                        "transaction_type": "B", 
                        "validity": "DAY", 
                        "amo": "NO", 
                        "tag": new_tag
                    }
                    
                    # Execute synchronous API order call against active broker infrastructure
                    if client.place_order(**params):
                        set_cooling(side)
                        print(f"{Fore.GREEN}✅ SUCCESS: {side} NATIVELY AVERAGED by {active_exit} tracking engine. Tag: {new_tag}")
                        
                except Exception as e:
                    logger.error(f"Order placement critical tracking failure on side {side}: {e}", exc_info=True)
                    print(f"{Fore.RED}⚠️ ORDER PLACEMENT CRITICAL ERROR: {e}")

