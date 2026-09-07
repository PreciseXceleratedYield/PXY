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
    Executes automated flat directional matrix averaging loops for derivative 
    positions based on single-run snapshots and structural exposure.
    """
    if df is None or df.empty: 
        return 
        
    now = datetime.now(IST).time() 
    if not REBUY_ENABLED or not (MARKET_START <= now <= MARKET_END): 
        return 

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
    
    ce_lots = int(ce_match.group(1)) if ce_match else 0
    pe_lots = int(pe_match.group(1)) if pe_match else 0  
    
    # Aggregate dimensional matrix groupings
    ce_rows = working_df[working_df['side'] == 'CE']
    pe_rows = working_df[working_df['side'] == 'PE']
    
    # Performance percentage tracking matrices
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

    ce_avg_loss = -ce_overall_pnl_pct if ce_overall_pnl_pct < 0 else 0.0
    pe_avg_loss = -pe_overall_pnl_pct if pe_overall_pnl_pct < 0 else 0.0
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
    
    ce_power = safe_float(ce_last.get("ce_power") or ce_last.get("ce_p", 1.0))
    ce_depth = safe_float(ce_last.get("hkin_ce_depth") or ce_last.get("ce_d", 1.0))
    pe_power = safe_float(pe_last.get("pe_power") or pe_last.get("pe_p", 1.0))
    pe_depth = safe_float(pe_last.get("hkin_pe_depth") or pe_last.get("pe_d", 1.0))
    
    ce_matrix_self = max(ce_depth, ce_power)
    pe_matrix_self = max(pe_depth, pe_power)
    
    # 🎯 BUG RESOLVED: Explicit series location restoration
    atr = safe_float(working_df['atr'].iloc[0]) if 'atr' in working_df.columns and not working_df.empty else 0.0
    
    raw_val = (atr * atr) + (atr + atr)
    dampened_val = max(24, min(raw_val, 76))
    
    ce_tgt = int(round(((atr / ce_lots) * ce_matrix_self))) if ce_lots > 0 else 0
    pe_tgt = int(round(((atr / pe_lots) * pe_matrix_self))) if pe_lots > 0 else 0

    ce_avg_entry = str(ce_last.get("entry", "NONE")).upper().strip() if not ce_rows.empty else "NONE"
    pe_avg_entry = str(pe_last.get("entry", "NONE")).upper().strip() if not pe_rows.empty else "NONE"

    supertrend = str(pe_last.get("supertrend", "NONE")).upper().strip() if not pe_rows.empty else "NONE"
    boss = str(pe_last.get("bos_val", "NONE")).upper().strip() if not pe_rows.empty else "NONE"
    
    # --- CLEAN DIRECT INVESTMENT ADJUSTED DRAWDOWN LIMITS ---
    ce_base_drawdown_limit = -atr * 1.4
    if "MBUY" in ce_avg_entry:
        ce_dynamic_threshold = ce_base_drawdown_limit * ce_invst_factor
    else:
        ce_dynamic_threshold = (-dampened_val * 2) if boss == "NSELL" else -dampened_val
    
    pe_base_drawdown_limit = -atr * 1.4
    if "MSELL" in pe_avg_entry:
        pe_dynamic_threshold = pe_base_drawdown_limit * pe_invst_factor
    else:
        pe_dynamic_threshold = (-dampened_val * 2) if boss == "NBUY" else -dampened_val

    ce_agt = int(round(ce_dynamic_threshold))
    pe_agt = int(round(pe_dynamic_threshold))
    
    ce_target_crossed = ce_avg_profit >= ce_tgt if ce_lots > 0 else False
    pe_target_crossed = pe_avg_profit >= pe_tgt if pe_lots > 0 else False

    ce_sts = "✔️" if ce_target_crossed else "❌"
    pe_sts = "✔️" if pe_target_crossed else "❌"
    # =============================================================================
    # PART 2: TELEMETRY STREAM PANEL GRAPHICS & BALANCED GEOMETRIC RATIO BAR
    # =============================================================================
    P_WIDTH = 40
    print("\n" + Fore.CYAN + "=" * P_WIDTH)
    print(Fore.CYAN + " OPT LOT  AGT STS TGT                PNL")
    print(Fore.CYAN + "-" * P_WIDTH)
    
    ce_pnl_val = int(round(ce_pnl))
    ce_pnl_color = Fore.CYAN + Style.BRIGHT if ce_target_crossed else (Fore.GREEN if ce_pnl_val >= 0 else Fore.RED)
    print(Fore.WHITE + f"{'CE':>4} {ce_lots:>3} {ce_agt:>4} {ce_sts:>3} {ce_tgt:>3} " + ce_pnl_color + f"{ce_pnl_val:>18}" + Style.RESET_ALL)
    
    pe_pnl_val = int(round(pe_pnl))
    pe_pnl_color = Fore.CYAN + Style.BRIGHT if pe_target_crossed else (Fore.GREEN if pe_pnl_val >= 0 else Fore.RED)
    print(Fore.WHITE + f"{'PE':>4} {pe_lots:>3} {pe_agt:>4} {pe_sts:>3} {pe_tgt:>3} " + pe_pnl_color + f"{pe_pnl_val:>18}" + Style.RESET_ALL)
    print(Fore.CYAN + "-" * P_WIDTH)

    ce_weight_int = int(round(ce_investment))
    pe_weight_int = int(round(pe_investment))
    left_label = f"{ce_weight_int}"
    right_label = f"{pe_weight_int}"
    
    track_slots = P_WIDTH - len(left_label) - len(right_label) - 6
    total_weight = ce_investment + pe_investment
    ce_ratio = ce_investment / total_weight if total_weight > 0 else 0.5
    
    left_dashes_count = max(0, min(track_slots, int(round(ce_ratio * track_slots))))
    right_dashes_count = max(0, track_slots - left_dashes_count)
    
    print("  " + Fore.GREEN + left_label + Fore.GREEN + ("━" * left_dashes_count) + Fore.WHITE + "⚖️" + Fore.RED + ("━" * right_dashes_count) + Fore.RED + right_label)
    print(Fore.CYAN + "=" * P_WIDTH + "\n")
    # =============================================================================
    # PART 3: ZERO-LOOP SINGLE RUN AUTOMATED SNAPSHOT ROUTING ENGINE
    # =============================================================================
    
    # -------------------------------------------------------------------------
    # 🟢 CALL OPTION (CE) SIDE ABSOLUTE EXECUTION SNAPSHOT
    # -------------------------------------------------------------------------
    if not ce_rows.empty and not is_cooling("CE") and len(ce_rows) < (MAX_LAYERS + 1):
        ce_last_row = ce_rows.iloc[-1]
        ce_symbol = ce_last_row['symbol']
        ce_qty = abs(int(safe_float(ce_last_row.get('qty', 0.0))))
        ce_final_loss = get_loss(ce_last_row)
        
        # ⚡ Rule Check A: Trending Momentum Override (Calls External Script Route)
        ce_force_script = (supertrend == "BULL" and "MBUY" in ce_avg_entry and ce_investment < pe_investment)
        
        # ⚖️ Rule Check B: Standard Drawdown Risk (Requires crossing threshold; active for SIDE trends)
        ce_crossed_threshold = (supertrend == "SIDE" and "MBUY" in ce_avg_entry and ce_dynamic_threshold > ce_final_loss)
        
        # 🚀 Execute if trending momentum is satisfied OR if the calculated side drawdown threshold is crossed
        if ce_force_script or ce_crossed_threshold:
            
            # ROUTE 1: Trending Macro Momentum -> Calls the external scale-up script
            if ce_force_script:
                logger.info("⚡ CE SNAPSHOT: BULL + MBUY. CE Investment lower. Forcing SCRIPT execution pipeline.")
                print_pxy_trigger_dashboard(
                    "CE", ce_symbol, ce_final_loss, ce_dynamic_threshold, "AUTO_MANAGED", 
                    ce_lots, pe_lots, ce_avg_entry
                )
                exe_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "exeforcepxy.py")
                if os.path.exists(exe_path):
                    try:
                        subprocess.run(["python3", exe_path, "1"], check=True)
                        set_cooling("CE")
                        print(f"{Fore.GREEN}✅ SUCCESS: CE Terminal Expansion Pipeline Called via Flag 1.")
                    except Exception as e:
                        logger.error(f"CE Subprocess shell execution failure: {e}", exc_info=True)
                else:
                    print(f"{Fore.RED}❌ CRITICAL FILE ERROR: Script missing at {exe_path}")
            
            # ROUTE 2: Sideways Market Pullback -> Places the order natively inline
            elif ce_crossed_threshold:
                logger.info("⚖️ CE SNAPSHOT: SIDE + MBUY Pullback. Executing native inline placement.")
                try:
                    new_tag = generate_pxy_tag()
                    print_pxy_trigger_dashboard(
                        "CE", ce_symbol, ce_final_loss, ce_dynamic_threshold, new_tag, 
                        ce_lots, pe_lots, ce_avg_entry
                    )
                    params = {
                        "exchange_segment": "nse_fo", "product": "NRML", "price": "0", "order_type": "MKT", 
                        "quantity": str(ce_qty), "trading_symbol": str(ce_symbol), "transaction_type": "B", 
                        "validity": "DAY", "amo": "NO", "tag": new_tag
                    }
                    if client.place_order(**params):
                        set_cooling("CE")
                        print(f"{Fore.GREEN}✅ SUCCESS: CE Natively Averaged via threshold crossover. Tag: {new_tag}")
                except Exception as e:
                    logger.error(f"CE Native placement tracking error: {e}", exc_info=True)

    # -------------------------------------------------------------------------
    # 🔴 PUT OPTION (PE) SIDE ABSOLUTE EXECUTION SNAPSHOT
    # -------------------------------------------------------------------------
    if not pe_rows.empty and not is_cooling("PE") and len(pe_rows) < (MAX_LAYERS + 1):
        pe_last_row = pe_rows.iloc[-1]
        pe_symbol = pe_last_row['symbol']
        pe_qty = abs(int(safe_float(pe_last_row.get('qty', 0.0))))
        pe_final_loss = get_loss(pe_last_row)
        
        # ⚡ Rule Check A: Trending Momentum Override (Calls External Script Route)
        pe_force_script = (supertrend == "BEAR" and "MSELL" in pe_avg_entry and pe_investment < ce_investment)
        
        # ⚖️ Rule Check B: Standard Drawdown Risk (Requires crossing threshold; active for SIDE trends)
        pe_crossed_threshold = (supertrend == "SIDE" and "MSELL" in pe_avg_entry and pe_dynamic_threshold > pe_final_loss)
        
        # 🚀 Execute if trending momentum is satisfied OR if the calculated side drawdown threshold is crossed
        if pe_force_script or pe_crossed_threshold:
            
            # ROUTE 1: Trending Macro Momentum -> Calls the external scale-up script
            if pe_force_script:
                logger.info("⚡ PE SNAPSHOT: BEAR + MSELL. PE Investment lower. Forcing SCRIPT execution pipeline.")
                print_pxy_trigger_dashboard(
                    "PE", pe_symbol, pe_final_loss, pe_dynamic_threshold, "AUTO_MANAGED", 
                    ce_lots, pe_lots, pe_avg_entry
                )
                exe_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "exeforcepxy.py")
                if os.path.exists(exe_path):
                    try:
                        subprocess.run(["python3", exe_path, "2"], check=True)
                        set_cooling("PE")
                        print(f"{Fore.GREEN}✅ SUCCESS: PE Terminal Expansion Pipeline Called via Flag 2.")
                    except Exception as e:
                        logger.error(f"PE Subprocess shell execution failure: {e}", exc_info=True)
                else:
                    print(f"{Fore.RED}❌ CRITICAL FILE ERROR: Script missing at {exe_path}")
            
            # ROUTE 2: Sideways Market Pullback -> Places the order natively inline
            elif pe_crossed_threshold:
                logger.info("⚖️ PE SNAPSHOT: SIDE + MSELL Pullback. Executing native inline placement.")
                try:
                    new_tag = generate_pxy_tag()
                    print_pxy_trigger_dashboard(
                        "PE", pe_symbol, pe_final_loss, pe_dynamic_threshold, new_tag, 
                        ce_lots, pe_lots, pe_avg_entry
                    )
                    params = {
                        "exchange_segment": "nse_fo", "product": "NRML", "price": "0", "order_type": "MKT", 
                        "quantity": str(pe_qty), "trading_symbol": str(pe_symbol), "transaction_type": "B", 
                        "validity": "DAY", "amo": "NO", "tag": new_tag
                    }
                    if client.place_order(**params):
                        set_cooling("PE")
                        print(f"{Fore.GREEN}✅ SUCCESS: PE Natively Averaged via threshold crossover. Tag: {new_tag}")
                except Exception as e:
                    logger.error(f"PE Native placement tracking error: {e}", exc_info=True)

