# =============================================================================
# MAIN MODULE: exeavgpxy.py
# UNIFIED STRUCTURAL DATA AGGREGATION & TELEMETRY ENGINE
# =============================================================================
import re
import os
import json
import logging
from datetime import datetime
from colorama import Fore, Style

# Import the isolated components
from exeagtpxy import getexeagtpxy
from exeagxpxy import execute_side_averaging_matrix

# Direct module dependency linking to inherit essential infrastructure variables
from exehvgpxy import (
    REBUY_ENABLED, MAX_LAYERS, IST, MARKET_START, MARKET_END,
    safe_float, get_loss
)
from run.runpchkpxy import get_position_summary

# Configure localized robust module logger
logger = logging.getLogger("exeavgpxy")

# -------------------------------------------------------------------------
# 🎛️ RISK CONFIGURATION MATRIX SWITCH
# -------------------------------------------------------------------------
USE_OVERALL_LOSS = True  # True = Overall Average Loss | False = Least Loss Layer Per Side


def print_telemetry_dashboard(p):
    """Constructs the visual geometric dashboard panel layout within a strict 40-char width."""
    if not p:
        return
    ce_agt = int(round(p["ce_dynamic_threshold"]))
    pe_agt = int(round(p["pe_dynamic_threshold"]))
    
    ce_target_crossed = p["ce_avg_profit"] >= p["ce_tgt"] if p["ce_lots"] > 0 else False
    pe_target_crossed = p["pe_avg_profit"] >= p["pe_tgt"] if p["pe_lots"] > 0 else False

    # Clean 2-char ASCII states to protect space alignment
    ce_sts = "OK" if ce_target_crossed else "NO"
    pe_sts = "OK" if pe_target_crossed else "NO"
    
    P_WIDTH = 40 
    print("\n" + Fore.CYAN + "=" * P_WIDTH)
    print(Fore.CYAN + " OPT  LOT   LGT   AGT  STS  TGT      PNL")
    print(Fore.CYAN + "-" * P_WIDTH)
    
    ce_lgt = int(round(p["ce_lgt"]))
    ce_pnl_val = int(round(p["ce_pnl"]))
    ce_pnl_color = Fore.CYAN + Style.BRIGHT if ce_target_crossed else (Fore.GREEN if ce_pnl_val >= 0 else Fore.RED)
    print(Fore.WHITE + f"{'CE':>4} {p['ce_lots']:>4} {ce_lgt:>5} {ce_agt:>5} {ce_sts:>4} {p['ce_tgt']:>4} " + ce_pnl_color + f"{ce_pnl_val:>8}" + Style.RESET_ALL)
    
    pe_lgt = int(round(p["pe_lgt"]))
    pe_pnl_val = int(round(p["pe_pnl"]))
    pe_pnl_color = Fore.CYAN + Style.BRIGHT if pe_target_crossed else (Fore.GREEN if pe_pnl_val >= 0 else Fore.RED)
    print(Fore.WHITE + f"{'PE':>4} {p['pe_lots']:>4} {pe_lgt:>5} {pe_agt:>5} {pe_sts:>4} {p['pe_tgt']:>4} " + pe_pnl_color + f"{pe_pnl_val:>8}" + Style.RESET_ALL)
    print(Fore.CYAN + "-" * P_WIDTH)

    ce_investment = p.get("ce_investment", 0.0)
    pe_investment = p.get("pe_investment", 0.0)
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

    super_trend = str(latest_row.get("supertrend", "NONE")).upper().strip()
    active_exit = str(latest_row.get("exit", "NONE")).upper().strip()
    
    ce_dynamic_threshold, pe_dynamic_threshold = getexeagtpxy(atr, ce_invst_factor, pe_invst_factor, active_exit, super_trend)

    # 🎛️ CORE PROFILE SWITCH: TRACK OVERALL OR COMPUTE THE LEAST LOSS POSITION LAYER
    if USE_OVERALL_LOSS:
        ce_lgt_val = ce_overall_pnl_pct
        pe_lgt_val = pe_overall_pnl_pct
    else:
        # Math Check: Since losses are signed negatives (e.g., -5% vs -35%), .max() extracts the least loss value.
        ce_lgt_val = ce_rows.apply(get_loss, axis=1).max() if not ce_rows.empty else 0.0
        pe_lgt_val = pe_rows.apply(get_loss, axis=1).max() if not pe_rows.empty else 0.0

    ce_agt = int(round(ce_dynamic_threshold))
    pe_agt = int(round(pe_dynamic_threshold))
    ce_target_crossed = ce_avg_profit >= ce_tgt if ce_lots > 0 else False
    pe_target_crossed = pe_avg_profit >= pe_tgt if pe_lots > 0 else False
    ce_sts = "OK" if ce_target_crossed else "NO"
    pe_sts = "OK" if pe_target_crossed else "NO"

    p_packet = {
        "ce_lots": ce_lots, "pe_lots": pe_lots, "ce_tgt": ce_tgt, "pe_tgt": pe_tgt, 
        "ce_pnl": ce_pnl, "pe_pnl": pe_pnl, "ce_avg_profit": ce_avg_profit, "pe_avg_profit": pe_avg_profit,
        "ce_investment": ce_investment, "pe_investment": pe_investment,
        "ce_dynamic_threshold": ce_dynamic_threshold, "pe_dynamic_threshold": pe_dynamic_threshold,
        "ce_lgt": ce_lgt_val, "pe_lgt": pe_lgt_val,
        "console_dump": {
            "header": " OPT  LOT   LGT   AGT  STS  TGT      PNL",
            "ce_line": f"{'CE':>4} {ce_lots:>4} {int(round(ce_lgt_val)):>5} {ce_agt:>5} {ce_sts:>4} {ce_tgt:>4} {int(round(ce_pnl)):>8}",
            "pe_line": f"{'PE':>4} {pe_lots:>4} {int(round(pe_lgt_val)):>5} {pe_agt:>5} {pe_sts:>4} {pe_tgt:>4} {int(round(pe_pnl)):>8}"
        }
    }

    print_telemetry_dashboard(p_packet)

    try:
        output_path = "../web/webavgpxy.json"
        dir_name = os.path.dirname(output_path)
        if dir_name and not os.path.exists(dir_name):
            os.makedirs(dir_name, exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(p_packet, f, indent=2)
    except Exception as json_err:
        logger.error(f"Failed to dump telemetry matrix payload to json: {json_err}")

    # Dispatch tracking metrics down to executor engine
    execute_side_averaging_matrix(
        client=client, 
        ce_rows=ce_rows, 
        pe_rows=pe_rows, 
        ce_lgt_val=ce_lgt_val, 
        pe_lgt_val=pe_lgt_val, 
        ce_dynamic_threshold=ce_dynamic_threshold, 
        pe_dynamic_threshold=pe_dynamic_threshold, 
        ce_lots=ce_lots, 
        pe_lots=pe_lots
    )

