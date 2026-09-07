# =============================================================================
# MAIN MODULE: exeavgpxy.py [PART 1: SYSTEM PATHS, IMPORTS & DATA MATRICES]
# =============================================================================
import re
import os
import logging
import subprocess
from datetime import datetime
from colorama import Fore, Style

# Direct module dependency linking to inherit all variables from the helper script
from exehvgpxy import (
    REBUY_ENABLED, MAX_LAYERS, IST, MARKET_START, MARKET_END,
    pxysqrce, pxysqrpe, safe_float, generate_pxy_tag, is_cooling,
    set_cooling, get_loss, print_pxy_trigger_dashboard
)
from run.runpchkpxy import get_position_summary

# Configure localized robust module logger
logger = logging.getLogger("exeavgpxy")

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
    working_df['row_invested'] = working_df['qty'].apply(safe_float) * (
        (working_df['sell_prc'].apply(safe_float) + working_df['buy_prc'].apply(safe_float)) / 2.0
    )
    
    # Shield against missing pnl column series failure
    if 'pnl' in working_df.columns:
        working_df['row_pnl'] = working_df['pnl'].apply(safe_float)
    else:
        working_df['row_pnl'] = 0.0

    # Compile explicit state summaries from position snapshots
    pos_raw = str(get_position_summary(client)).upper().replace(" ", "").strip()
    
    ce_match = re.search(r'(\d+)CE', pos_raw)
    pe_match = re.search(r'(\d+)PE', pos_raw)
    
    # 🎯 FIX 1: Synced to use group(1) since single match parenthetical arrays only contain index 1
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
    # =====================================================================
    # 📉 RISK & LOSS TRACKING GROUP (Flipped to Positive Magnitudes)
    # =====================================================================
    # Tracks the raw magnitude of your downside risk. 
    # Captures losses only; returns 0.0 if the position is winning or flat.
    ce_avg_loss = -ce_overall_pnl_pct if ce_overall_pnl_pct < 0 else 0.0
    pe_avg_loss = -pe_overall_pnl_pct if pe_overall_pnl_pct < 0 else 0.0
    
    # =====================================================================
    # 📈 TARGET & PROFIT TRACKING GROUP (Pure Positive Performance)
    # =====================================================================
    # Tracks the raw magnitude of your upside performance.
    # Captures profits only; returns 0.0 if the position is losing or flat.
    ce_avg_profit = ce_overall_pnl_pct if ce_overall_pnl_pct > 0 else 0.0
    pe_avg_profit = pe_overall_pnl_pct if pe_overall_pnl_pct > 0 else 0.0

    # Structural exposure factor resolutions
    ce_investment = float(ce_rows['row_invested'].sum()) if not ce_rows.empty else 0.0
    pe_investment = float(pe_rows['row_invested'].sum()) if not pe_rows.empty else 0.0
    
    ce_invst_factor = ce_investment / pe_investment if (ce_investment > 0 and pe_investment > 0) else 1.0
    pe_invst_factor = pe_investment / ce_investment if (ce_investment > 0 and pe_investment > 0) else 1.0
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
    
    # 🎯 FIX 2: Moved up here so raw_val is fully initialized before the target formula loop tries to evaluate variables!
    raw_val = (atr * atr) + (atr + atr)
    dampened_val = max(24, min(raw_val, 76))
    
    ce_tgt = int(round(((atr / ce_lots) * ce_matrix_self))) if ce_lots > 0 else 0
    pe_tgt = int(round(((atr / pe_lots) * pe_matrix_self))) if pe_lots > 0 else 0

    # Extract exit fields directly from the side snapshots since they are identical across rows
    ce_avg_entry = str(ce_last.get("entry", "NONE")).upper().strip() if not ce_rows.empty else "NONE"
    pe_avg_entry = str(pe_last.get("entry", "NONE")).upper().strip() if not pe_rows.empty else "NONE"

    # --- ZERO-DIVISION SHIELDED LOTS FACTOR ENGINE ---
    ce_lots_factor = 1 
    pe_lots_factor = 1 

    # --- PRE-CALCULATE DYNAMIC THRESHOLDS MULTIPLIED ACROSS THE WHOLE THING ---
    supertrend = (
        str(pe_last.get("supertrend", "NONE")).upper().strip()
        if not pe_rows.empty
        else "NONE"
    )
    boss = (
        str(pe_last.get("bos_val", "NONE")).upper().strip()
        if not pe_rows.empty
        else "NONE"
    )
    
    # --- SIMPLIFIED TREND FACTORS ---
    ce_trend_factor = 0.75 if supertrend == "BULL" else 1.0
    pe_trend_factor = 0.75 if supertrend == "BEAR" else 1.0
    
    # --- CALL OPTION (CE) SIDE RISK CALCULATIONS ---
    ce_base_drawdown_limit = -atr
    if "MBUY" in ce_avg_entry:
        ce_dynamic_threshold = ((ce_base_drawdown_limit * ce_invst_factor) + (ce_base_drawdown_limit * ce_trend_factor)) / 2 
    else:
        ce_dynamic_threshold = (-dampened_val * 2) if boss == "NSELL" else -dampened_val
    
    # --- PUT OPTION (PE) SIDE RISK CALCULATIONS ---
    pe_base_drawdown_limit = -atr
    if "MSELL" in pe_avg_entry:
        pe_dynamic_threshold = ((pe_base_drawdown_limit * pe_invst_factor) + (pe_base_drawdown_limit * pe_trend_factor)) / 2
    else:
        pe_dynamic_threshold = (-dampened_val * 2) if boss == "NBUY" else -dampened_val

    # 📊 VOLATILITY-UNIFIED AGT RESOLUTION LINKED TO COMBINED DYNAMIC THRESHOLDS
    ce_agt = int(round(ce_dynamic_threshold))
    pe_agt = int(round(pe_dynamic_threshold))
    
    # 🎯 MONITOR TARGET PERCENTAGE CROSSINGS (ACTUAL OVERALL LOSS >= POSITIVE TGT %)
    ce_target_crossed = ce_avg_profit >= ce_tgt if ce_lots > 0 else False
    pe_target_crossed = pe_avg_profit >= pe_tgt if pe_lots > 0 else False

    ce_sts = "✔️" if ce_target_crossed else "❌"
    pe_sts = "✔️" if pe_target_crossed else "❌"

    if ce_target_crossed and "MBUY" in ce_avg_entry:
        pass  

    if pe_target_crossed and "MSELL" in pe_avg_entry:
        pass  

    # =============================================================================
    # PART 6: TELEMETRY STREAM PANEL GRAPHICS & BALANCED GEOMETRIC RATIO BAR
    # =============================================================================
    P_WIDTH = 40
    
    print("\n" + Fore.CYAN + "=" * P_WIDTH)
    print(Fore.CYAN + " OPT LOT  AGT STS TGT                PNL")
    print(Fore.CYAN + "-" * P_WIDTH)
    
    # --- CE Row ---
    ce_pnl_val = int(round(ce_pnl))
    ce_pnl_color = Fore.CYAN + Style.BRIGHT if ce_target_crossed else (Fore.GREEN if ce_pnl_val >= 0 else Fore.RED)
    
    ce_opt_col = f"{'CE':>4} "         
    ce_lot_col = f"{ce_lots:>3} "      
    ce_agt_col = f"{ce_agt:>4} "       
    ce_sts_col = f"{ce_sts:>3} "       
    ce_tgt_col = f"{ce_tgt:>3} "       
    ce_pnl_str = f"{ce_pnl_val:>18}"
    print(Fore.WHITE + ce_opt_col + ce_lot_col + ce_agt_col + ce_sts_col + ce_tgt_col + ce_pnl_color + ce_pnl_str + Style.RESET_ALL)
    
    # --- PE Row ---
    pe_pnl_val = int(round(pe_pnl))
    pe_pnl_color = Fore.CYAN + Style.BRIGHT if pe_target_crossed else (Fore.GREEN if pe_pnl_val >= 0 else Fore.RED)
    
    pe_opt_col = f"{'PE':>4} "
    pe_lot_col = f"{pe_lots:>3} "
    pe_agt_col = f"{pe_agt:>4} "
    pe_sts_col = f"{pe_sts:>3} "
    pe_tgt_col = f"{pe_tgt:>3} "
    pe_pnl_str = f"{pe_pnl_val:>18}"
    
    print(Fore.WHITE + pe_opt_col + pe_lot_col + pe_agt_col + pe_sts_col + pe_tgt_col + pe_pnl_color + pe_pnl_str + Style.RESET_ALL)
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
    # PART 7: MULTI-LAYER DOWNWARD DIRECTIONAL MATRIX AVERAGING LOOPS
    # =============================================================================
    # EXECUTION TOGGLE: "SCRIPT" for terminal pipeline execution, "AVERAGE" for native inline order
    EXECUTION_MODE = "AVERAGE"

    for side in ['CE', 'PE']:
        side_df = ce_rows if side == 'CE' else pe_rows
        if side_df.empty:
            continue
            
        last_row = side_df.iloc[-1]
        active_exit = ce_avg_entry if side == 'CE' else pe_avg_entry
    
        all_positions_crossed_threshold = True
        dynamic_threshold = ce_dynamic_threshold if side == 'CE' else pe_dynamic_threshold
        last_calculated_threshold = dynamic_threshold
        
        # --- SCAN INDIVIDUAL POSITION ROWS ---
        for _, row in side_df.iterrows():
            pos_loss = get_loss(row)
            
            # 🎯 ORIGINAL NEGATIVE LOGIC COMPLETELY PRESERVED AS VERIFIED CORRECT
            if not (dynamic_threshold > pos_loss):
                all_positions_crossed_threshold = False
                break
                
        # --- PLACE LIVE SYSTEM AVERAGING ORDER ---
        if all_positions_crossed_threshold and len(side_df) < (MAX_LAYERS + 1):
            if not is_cooling(side):
                symbol = last_row['symbol']
                qty = abs(int(safe_float(last_row.get('qty', 0.0))))
                final_loss = get_loss(last_row)
                
                # --- OPTION BRANCH 1: NATIVE INLINE ORDER PLACEMENT ---
                if EXECUTION_MODE == "AVERAGE":
                    new_tag = generate_pxy_tag()
                    print_pxy_trigger_dashboard(
                        side, symbol, final_loss, last_calculated_threshold, new_tag, 
                        ce_lots, pe_lots, active_exit
                    )
                    try:
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
                        if client.place_order(**params):
                            set_cooling(side)
                            print(f"{Fore.GREEN}✅ SUCCESS: {side} NATIVELY AVERAGED by {active_exit} tracking engine. Tag: {new_tag}")
                    except Exception as e:
                        logger.error(f"Order placement critical tracking failure on side {side}: {e}", exc_info=True)
                        print(f"{Fore.RED}⚠️ ORDER PLACEMENT CRITICAL ERROR: {e}")

                # --- OPTION BRANCH 2: SUBPROCESS SCRIPT PIPELINE TERMINAL ROUTE ---
                elif EXECUTION_MODE == "SCRIPT":
                    print_pxy_trigger_dashboard(
                        side, symbol, final_loss, last_calculated_threshold, "AUTO_MANAGED", 
                        ce_lots, pe_lots, active_exit
                    )
                    
                    # Dynamic absolute base path to the target script file
                    exe_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "exeforcepxy.py")
                    
                    if os.path.exists(exe_path):
                        try:
                            # 1️⃣ Map system script positional argument based on contract side
                            action_flag = "1" if side == "CE" else "2"
                            cmd = ["python3", exe_path, action_flag]
                            
                            # 2️⃣ Execute live terminal order command cleanly via shell pipeline
                            subprocess.run(cmd, check=True)
                            
                            # 3️⃣ Success tracking update
                            set_cooling(side)
                            print(f"{Fore.GREEN}✅ SUCCESS: {side} Averaging triggered via absolute path execution.")
                            
                        except subprocess.CalledProcessError as e:
                            logger.error(f"Absolute shell execution failure on exeforcepxy.py: {e}", exc_info=True)
                            print(f"{Fore.RED}⚠️ TERMINAL PIPELINE EXECUTION ERROR: {e}")
                        except Exception as e:
                            logger.error(f"Critical execution tracking failure on side {side}: {e}", exc_info=True)
                            print(f"{Fore.RED}⚠️ CRITICAL INTEGRATION ERROR: {e}")
                    else:
                        print(f"{Fore.RED}❌ CRITICAL FILE ERROR: Target script not found at {exe_path}")

