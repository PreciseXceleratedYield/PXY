# =============================================================================
# MAIN CONTROLLER MODULE: exeavgpxy.py (avg)
# MASTER TELEMETRY ORCHESTRATOR & AGGREGATION LOOP
# =============================================================================
import re
import os
import json
import logging
from datetime import datetime
from colorama import Fore, Style

from exeagtpxy import getexeagtpxy, is_aligned, execute_side_averaging_matrix
from exeaxgpxy import run_target_engine

# SYNCHRONIZED TO CORE VARIABLES & GUARDS MODULAR LAYER (acg)
from exeacgpxy import (
    REBUY_ENABLED, MAX_LAYERS, IST, MARKET_START, MARKET_END,
    safe_float, get_loss, side_overall_pnl_pct
)
from run.runpchkpxy import get_position_summary

logger = logging.getLogger("exeavgpxy")

# System A & B unified to monitor aggregate bulk position metrics
USE_OVERALL_LOSS = True


def print_telemetry_dashboard(p):
    """Streamlined dashboard: RUN column cleanly arranged between LGT and TGT."""
    if not p:
        return
    P_WIDTH = 36
    print("\n" + Fore.CYAN + "=" * P_WIDTH)
    print(Fore.CYAN + " OPT  LOT   LGT   RUN   TGT      PNL")
    print(Fore.CYAN + "-" * P_WIDTH)

    for side in ("ce", "pe"):
        lots = p[f"{side}_lots"]
        lgt = int(round(p[f"{side}_lgt"]))
        tgt_txt = "99" if p[f"{side}_aligned"] else "1.4+"
        pnl_val = int(round(p[f"{side}_pnl"]))
        run_pct_val = int(round(p[f"{side}_run_pct"]))
        decision = p[f"{side}_decision"].upper()

        pnl_color = (Fore.CYAN + Style.BRIGHT) if decision == "SQUARE_OFF" else (Fore.GREEN if pnl_val >= 0 else Fore.RED)

        print(Fore.WHITE + f"{side.upper():>4} {lots:>4} {lgt:>5} {run_pct_val:>5} {tgt_txt:>5} "
              + pnl_color + f"{pnl_val:>8}" + Style.RESET_ALL)

    print(Fore.CYAN + "-" * P_WIDTH)
    ce_inv, pe_inv = p.get("ce_investment", 0.0), p.get("pe_investment", 0.0)
    left_label, right_label = f"{int(round(ce_inv))}", f"{int(round(pe_inv))}"
    track_slots = P_WIDTH - len(left_label) - len(right_label) - 6
    total = ce_inv + pe_inv
    ce_ratio = ce_inv / total if total > 0 else 0.5
    left_n = max(0, min(track_slots, int(round(ce_ratio * track_slots))))
    right_n = max(0, track_slots - left_n)
    print("  " + Fore.GREEN + left_label + ("━" * left_n) + Fore.WHITE + "⚖️" + Fore.RED + ("━" * right_n) + Fore.RED + right_label)
    print(Fore.CYAN + "=" * P_WIDTH + "\n")


def handle_side_averaging(client, df):
    """Runs System A (averaging) and System B (target/exit/fresh-entry) each cycle."""
    if df is None or df.empty:
        return
    now = datetime.now(IST).time()
    if not REBUY_ENABLED or not (MARKET_START <= now <= MARKET_END):
        return

    working_df = df.copy()
    working_df['side'] = working_df['symbol'].astype(str).str[-2:].str.upper()
    working_df['row_invested'] = working_df['qty'].apply(safe_float) * (
        (working_df['buy_prc'].apply(safe_float) + working_df['sell_prc'].apply(safe_float)) / 2.0
    )
    working_df['row_pnl'] = working_df['pnl'].apply(safe_float) if 'pnl' in working_df.columns else 0.0

    pos_raw = str(get_position_summary(client)).upper().replace(" ", "").strip()
    ce_match = re.search(r'(\d+)CE', pos_raw)
    pe_match = re.search(r'(\d+)PE', pos_raw)
    ce_lots = int(ce_match.group(1)) if ce_match else 0
    pe_lots = int(pe_match.group(1)) if pe_match else 0

    ce_rows = working_df[working_df['side'] == 'CE']
    pe_rows = working_df[working_df['side'] == 'PE']

    ce_overall_pnl_pct = side_overall_pnl_pct(ce_rows)
    pe_overall_pnl_pct = side_overall_pnl_pct(pe_rows)
    ce_avg_profit = ce_overall_pnl_pct if ce_overall_pnl_pct > 0 else 0.0
    pe_avg_profit = pe_overall_pnl_pct if pe_overall_pnl_pct > 0 else 0.0

    ce_investment = float(ce_rows['row_invested'].sum()) if not ce_rows.empty else 0.0
    pe_investment = float(pe_rows['row_invested'].sum()) if not pe_rows.empty else 0.0
    ce_invst_factor = ce_investment / pe_investment if (ce_investment > 0 and pe_investment > 0) else 1.0
    pe_invst_factor = pe_investment / ce_investment if (ce_investment > 0 and pe_investment > 0) else 1.0

    ce_pnl = float(ce_rows['row_pnl'].sum()) if not ce_rows.empty else 0.0
    pe_pnl = float(pe_rows['row_pnl'].sum()) if not pe_rows.empty else 0.0

    active_exit = str(working_df.iloc[-1].get("exit", "NONE")).upper().strip()
    ce_aligned = is_aligned("CE", active_exit)
    pe_aligned = is_aligned("PE", active_exit)

    ce_dynamic_threshold, pe_dynamic_threshold = getexeagtpxy(ce_invst_factor, pe_invst_factor)

    if USE_OVERALL_LOSS:
        ce_lgt_val, pe_lgt_val = ce_overall_pnl_pct, pe_overall_pnl_pct
    else:
        ce_lgt_val = ce_rows.apply(get_loss, axis=1).max() if not ce_rows.empty else 0.0
        pe_lgt_val = pe_rows.apply(get_loss, axis=1).max() if not pe_rows.empty else 0.0

    # System B Evaluation Engine
    b_result = run_target_engine(active_exit, ce_rows, pe_rows, ce_avg_profit, pe_avg_profit, ce_lots, pe_lots)
    ce_decision, pe_decision = b_result["CE"][0], b_result["PE"][0]

    p_packet = {
        "ce_lots": ce_lots, "pe_lots": pe_lots,
        "ce_pnl": ce_pnl, "pe_pnl": pe_pnl,
        "ce_investment": ce_investment, "pe_investment": pe_investment,
        "ce_lgt": ce_dynamic_threshold, "pe_lgt": pe_dynamic_threshold,
        "ce_run_pct": ce_lgt_val, "pe_run_pct": pe_lgt_val,
        "ce_aligned": ce_aligned, "pe_aligned": pe_aligned,
        "ce_decision": ce_decision, "pe_decision": pe_decision,
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
        logger.error(f"Failed to dump telemetry payload to json: {json_err}")

    # System A Placement Engine Flow
    execute_side_averaging_matrix(
        client=client, ce_rows=ce_rows, pe_rows=pe_rows,
        ce_lgt_val=ce_lgt_val, pe_lgt_val=pe_lgt_val,
        ce_dynamic_threshold=ce_dynamic_threshold, pe_dynamic_threshold=pe_dynamic_threshold,
        ce_lots=ce_lots, pe_lots=pe_lots,
        ce_aligned=ce_aligned, pe_aligned=pe_aligned,
    )
