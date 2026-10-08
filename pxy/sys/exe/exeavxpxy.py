# =============================================================================
# AVERAGING CONTROLLER MODULE: exeavxpxy.py (avg)
# AVERAGING ORCHESTRATOR & TELEMETRY (no exits, no fresh buys)
# =============================================================================
import re
import os
import json
import logging
from datetime import datetime
from colorama import Fore, Style

from syscnfgpxy import (
    EXEAMSPXY_MAX_INVESTMENT,
    EXEAVXPXY_MARKET_END as MARKET_END,
    EXEAVXPXY_MARKET_START as MARKET_START,
    EXEAVXPXY_REBUY_ENABLED as REBUY_ENABLED,
    EXEAVXPXY_USE_OVERALL_LOSS,
    EXETGTPXY_MODE,
)
from sysdecisionpxy import (
    averaging_placement_allowed,
    averaging_window_enabled,
)
from exeagtpxy import is_aligned
from exeltgtpxy import calculate_lgt, target_price              # Import from central hub
from exeamspxy import execute_side_averaging_matrix

from exeacgpxy import (
    IST,
    safe_float, get_loss, side_overall_pnl_pct
)
from run.runpchkpxy import get_position_summary
from run.runexlckpxy import ledger_busy

logger = logging.getLogger("exeavxpxy")


def averaging_alignment_signals(
    exit_signal, direction, ce_investment, pe_investment, sma_status="NA"
):
    """Combine signal alignment with the SMA-50 side gate for averaging."""
    ce_aligned = is_aligned("CE", exit_signal)
    pe_aligned = is_aligned("PE", exit_signal)
    signal = str(direction).upper().strip()
    if EXETGTPXY_MODE == "DIRGT" and signal in {"UP", "DOWN"}:
        if ce_investment < pe_investment:
            ce_aligned = is_aligned("CE", "BULL" if signal == "UP" else "BEAR")
        elif pe_investment < ce_investment:
            pe_aligned = is_aligned("PE", "BULL" if signal == "UP" else "BEAR")
    sma = str(sma_status).upper().strip()
    ce_aligned = ce_aligned and sma == "BULL"
    pe_aligned = pe_aligned and sma == "BEAR"
    return ce_aligned, pe_aligned


def _side_target_pct(rows, ce_investment=0, pe_investment=0, ce_count=0, pe_count=0, is_ce=True):
    """Reports the existing per-lot exit target as a side-level percentage."""
    if rows.empty:
        return 0.0
    row = rows.iloc[-1]
    entry = safe_float(row.get("pxy_entry") or row.get("buy_prc"))
    if entry <= 0:
        return 0.0
    target = target_price(row, ce_investment, pe_investment, ce_count, pe_count)
    return max(0.0, ((target - entry) / entry) * 100.0)


# Averaging monitors the aggregate (blended) loss of each side
USE_OVERALL_LOSS = EXEAVXPXY_USE_OVERALL_LOSS

# Telemetry JSON for the web app: anchored to this file (same web/ folder as exeexppxy), never to the working directory
WEB_AVG_JSON_REL = "../../web/webavgpxy.json"


def print_telemetry_dashboard(p):
    """Streamlined dashboard: RUN = blended P&L% of the side, LGT = averaging trigger."""
    if not p:
        return
    P_WIDTH = 36
    print("\n" + Fore.CYAN + "=" * P_WIDTH)
    print(Fore.CYAN + " OPT  LOT   LGT   RUN  TGT      PNL")
    print(Fore.CYAN + "-" * P_WIDTH)

    for side in ("ce", "pe"):
        lots = p[f"{side}_lots"]
        lgt = int(round(p[f"{side}_lgt"]))

        pnl_val = int(round(p[f"{side}_pnl"]))
        run_pct_val = int(round(p[f"{side}_run_pct"]))
        tgt_pct_val = int(round(p[f"{side}_tgt"]))

        pnl_color = Fore.GREEN if pnl_val >= 0 else Fore.RED

        print(Fore.WHITE + f"{side.upper():>4} {lots:>4} {lgt:>5} {run_pct_val:>5} "
              f"{tgt_pct_val:>5} "
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
    """Runs System A (averaging) each cycle. Exits and counter-buys live in the exit pipe."""
    if df is None or df.empty:
        return
    now = datetime.now(IST).time()
    if not averaging_window_enabled(REBUY_ENABLED, now, MARKET_START, MARKET_END):
        return

    working_df = df.copy()
    working_df['side'] = working_df['symbol'].astype(str).str[-2:].str.upper()
    working_df['row_invested'] = working_df['qty'].apply(safe_float) * working_df['sell_prc'].apply(safe_float)
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

    ce_investment = float(ce_rows['row_invested'].sum()) if not ce_rows.empty else 0.0
    pe_investment = float(pe_rows['row_invested'].sum()) if not pe_rows.empty else 0.0

    ce_pnl = float(ce_rows['row_pnl'].sum()) if not ce_rows.empty else 0.0
    pe_pnl = float(pe_rows['row_pnl'].sum()) if not pe_rows.empty else 0.0

    # 🎯 STEP POSITIONS FIXED: Parse variable status first
    active_exit = str(working_df.iloc[-1].get("exit", "NONE")).upper().strip()
    active_direction = str(working_df.iloc[-1].get("direction", "NONE")).upper().strip()
    active_sma = str(working_df.iloc[-1].get("sma", "NA")).upper().strip()
    ce_aligned, pe_aligned = averaging_alignment_signals(
        active_exit, active_direction, ce_investment, pe_investment, active_sma
    )

    ce_dynamic_threshold = calculate_lgt(
        ce_investment,
        pe_investment,
        is_ce=True,
    )
    pe_dynamic_threshold = calculate_lgt(
        ce_investment,
        pe_investment,
        is_ce=False,
    )

    if USE_OVERALL_LOSS:
        ce_lgt_val, pe_lgt_val = ce_overall_pnl_pct, pe_overall_pnl_pct
    else:
        ce_lgt_val = ce_rows.apply(get_loss, axis=1).max() if not ce_rows.empty else 0.0
        pe_lgt_val = pe_rows.apply(get_loss, axis=1).max() if not pe_rows.empty else 0.0

    ce_tgt = _side_target_pct(ce_rows, ce_investment, pe_investment, ce_lots, pe_lots, is_ce=True)
    pe_tgt = _side_target_pct(pe_rows, ce_investment, pe_investment, ce_lots, pe_lots, is_ce=False)

    p_packet = {
        "ce_lots": ce_lots, "pe_lots": pe_lots,
        "ce_pnl": ce_pnl, "pe_pnl": pe_pnl,
        "ce_investment": ce_investment, "pe_investment": pe_investment,
        "ce_lgt": ce_dynamic_threshold, "pe_lgt": pe_dynamic_threshold,
        "ce_run_pct": ce_lgt_val, "pe_run_pct": pe_lgt_val,
        "ce_aligned": ce_aligned, "pe_aligned": pe_aligned,
        # Informational targets only; exit orders remain exclusively in the exit pipe.
        "ce_tgt": ce_tgt, "pe_tgt": pe_tgt,
        "ce_decision": "hold", "pe_decision": "hold",
    }

    print_telemetry_dashboard(p_packet)

    try:
        output_path = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), WEB_AVG_JSON_REL))
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        tmp_path = output_path + ".tmp"
        with open(tmp_path, "w") as f:
            json.dump(p_packet, f, indent=2)
        os.replace(tmp_path, output_path)
    except Exception as json_err:
        logger.error(f"Failed to dump telemetry payload to json: {json_err}")

    # Another process holds the ledger lock (a tick or a liquidation is running): place nothing this cycle
    is_ledger_busy = ledger_busy()
    if not averaging_placement_allowed(is_ledger_busy):
        print(f"{Fore.YELLOW}⚠️ Ledger lock held (tick or liquidation running); averaging skipped.")
        return

    # System A Placement Engine Flow
    execute_side_averaging_matrix(
        client=client, ce_rows=ce_rows, pe_rows=pe_rows,
        ce_lgt_val=ce_lgt_val, pe_lgt_val=pe_lgt_val,
        ce_dynamic_threshold=ce_dynamic_threshold, pe_dynamic_threshold=pe_dynamic_threshold,
        ce_lots=ce_lots, pe_lots=pe_lots,
        ce_aligned=ce_aligned, pe_aligned=pe_aligned,
        ce_investment=ce_investment, pe_investment=pe_investment,
        max_investment=EXEAMSPXY_MAX_INVESTMENT,
    )
