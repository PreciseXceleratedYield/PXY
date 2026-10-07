#!/usr/bin/env python3
# runexacpxy.py   (lives in ~/pxy/sys/exe/run/)
#
# MASTER RISK LEDGER orchestrator: Renko trailing stop + hard loss floor.
# Called from runlilopxy.process_lilo_orders (two hooks, see README_risk.md):
#   1) runexacpxy.daily_purge_check()                             top of process_lilo_orders
#   2) runexacpxy.execute_master_risk_ledger(client, open_df, closed_df)   after open_df / closed_df exist
#
# On a confirmed breach it squares off everything (exesqrpxy.py -all), waits until the broker is flat,
# locks the final loss into pnl_offset, resets the engine and ends the process with sys.exit(...).
#
# Same maths and web JSON files as exeexacpxy.py. Do NOT keep exeexacpxy.py scheduled as well.
#
# The ledger is split over six runex*pxy.py files; the file map is at the top of runexiopxy.py.
import os
import sys
import time
from pathlib import Path
from colorama import Fore, Style, init

SYS_DIR = Path(__file__).resolve().parents[2]
if str(SYS_DIR) not in sys.path:
    sys.path.insert(0, str(SYS_DIR))

from syscnfgpxy import (
    RUNEXACPXY_CNTRLRSKBAR,
    RUNEXACPXY_CNTRLRSKBAR_ACTIVATION_TIME,
    RUNEXACPXY_RISK_MODE,
    RUNEXACPXY_BREACH_TICKS_REQUIRED,
    RUNEXACPXY_DEBUG_ENABLED,
    RUNEXACPXY_LEDGER_BASIS_GUARD,
    RUNEXACPXY_RISK_ACTION,
    RUNEXACPXY_TICK_MIN_GAP_SECONDS,
    RUNEXACPXY_VIEW_ONLY_ENV,
)
from runexiopxy import now_ist, today_ist, RENKO_STATE_FILE, WEB_DIR, SQUAREOFF_SCRIPT_PATH  # noqa: F401
from runexmtpxy import (
    INITIAL_LOSS_FLOOR, PEAK_CEILING, compute_totals, compute_stop, force_zero_ending, _both_empty,
    midday_risk_activation_due,
)
from runexstpxy import (
    load_check_state, save_check_state, load_session_state, save_session_state,
    load_meta, save_meta, state_is_stale, purge_stale_cache, _current_filter_time,
)
from runexlckpxy import _acquire_lock, _release_lock, ledger_busy  # noqa: F401
from runexlqdpxy import liquidate_and_exit, run_squareoff, wait_until_flat  # noqa: F401

init(autoreset=True)

# ==================== CONFIG (this file's settings) ====================
RISK_ACTION = RUNEXACPXY_RISK_ACTION
RISK_CANDLE_CONTROL_ENABLED = (
    str(RUNEXACPXY_CNTRLRSKBAR).upper().strip() == "YES"
)
BREACH_TICKS_REQUIRED = RUNEXACPXY_BREACH_TICKS_REQUIRED
TICK_MIN_GAP_SECONDS = RUNEXACPXY_TICK_MIN_GAP_SECONDS
LEDGER_BASIS_GUARD = RUNEXACPXY_LEDGER_BASIS_GUARD
VIEW_ONLY_ENV = RUNEXACPXY_VIEW_ONLY_ENV
# =======================================================================

# Re-entrancy guard: the post-square-off ledger refresh calls process_lilo_orders again,
# which would call this module again.
_IN_LEDGER = False


def debug_log(msg, color=Fore.BLUE):
    if RUNEXACPXY_DEBUG_ENABLED:
        print(f"{color}[DEBUG] {msg}{Style.RESET_ALL}")


# ---------------------------------------------------------------------------
# HOOK 1: daily purge (runs before any broker call or data guard)
# ---------------------------------------------------------------------------
def daily_purge_check():
    """Clears yesterday's web JSON once per day, even before today's first trade exists.
    Only fires when the state file is missing or dated before today. Never raises."""
    if _IN_LEDGER:
        return
    can_run, fh = _acquire_lock()
    if not can_run:
        return
    try:
        if state_is_stale(load_session_state()):
            purge_stale_cache()
    except Exception as e:
        print(f"{Fore.YELLOW}⚠️ Stale check skipped (state unreadable): {e}")
    finally:
        _release_lock(fh)


# ---------------------------------------------------------------------------
# HOOK 2: the master ledger
# ---------------------------------------------------------------------------
def execute_master_risk_ledger(client, open_df, closed_df):
    """Defensive gatekeeper. Returns normally when there is nothing to do or the tick was skipped.
    On a confirmed breach: square-off, flat check, state reset, then sys.exit(...)."""
    global _IN_LEDGER
    if _IN_LEDGER:
        return
    if os.environ.get(VIEW_ONLY_ENV) == "1":
        debug_log("Ledger guard: view-only run; no tick counted.")
        return
    if _both_empty(open_df, closed_df):
        debug_log("Ledger guard: no ledger data; state untouched.")
        return

    can_run, lock_handle = _acquire_lock()
    if not can_run:
        debug_log("Ledger guard: another tick is running; skipping.")
        return

    _IN_LEDGER = True
    try:
        _tick(client, open_df, closed_df)
    except SystemExit:
        raise
    except Exception as e:
        print(f"{Fore.RED}⚠️ Master risk ledger error (tick skipped, ledger still returned): {e}")
    finally:
        _IN_LEDGER = False
        _release_lock(lock_handle)


def _tick(client, open_df, closed_df):
    # 1. Read state. A corrupt/locked file skips the tick rather than writing zeros.
    try:
        state_on_disk = load_session_state()
        check_state_on_disk = load_check_state()
    except Exception as e:
        print(f"{Fore.RED}⚠️ State file unreadable: {e}. Skipping tick. "
              f"If this repeats, fix or delete {RENKO_STATE_FILE}.")
        return

    # 2. Once-a-day override (backup for hook 1). Only a missing file or an earlier date counts as stale.
    session_state_is_stale = state_is_stale(state_on_disk)
    if session_state_is_stale:
        purge_stale_cache()
        historical_peak_record = 0.0
        pnl_offset = 0.0
        consecutive_breaches = 0
        risk_control_activated = False
    else:
        historical_peak_record = state_on_disk["session_peak_pnl"]
        pnl_offset = state_on_disk["pnl_offset"]
        consecutive_breaches = check_state_on_disk["consecutive_breaches"]
        risk_control_activated = state_on_disk["risk_control_activated"]

    # 3. One tick per cycle: the exit pipe and the avg pipe both load the ledger every cycle.
    meta = load_meta()
    now_epoch = time.time()
    if TICK_MIN_GAP_SECONDS > 0 and (now_epoch - meta["last_tick_epoch"]) < TICK_MIN_GAP_SECONDS:
        debug_log(f"Tick skipped: previous tick {now_epoch - meta['last_tick_epoch']:.1f}s ago "
                  f"(< {TICK_MIN_GAP_SECONDS}s).")
        return

    # 4. Ledger basis: if runlilopxy now starts its ledger later (FILTER_TIME moved after a square-off),
    #    the old offset belongs to a bigger ledger, so start a fresh game.
    current_basis = _current_filter_time()
    if LEDGER_BASIS_GUARD and current_basis is not None:
        stored_basis = meta.get("ledger_basis")
        if stored_basis is not None and stored_basis != current_basis:
            print(f"🔄 {Fore.CYAN}Ledger start changed ({stored_basis} -> {current_basis}). "
                  f"Starting a fresh game (offset, peak and breach count reset).")
            historical_peak_record = 0.0
            pnl_offset = 0.0
            consecutive_breaches = 0
            risk_control_activated = False
            save_check_state(0)
            save_session_state(0.0, 0.0, INITIAL_LOSS_FLOOR, 0.0)
        meta["ledger_basis"] = current_basis
    meta["last_tick_epoch"] = now_epoch
    save_meta(meta)

    # 5. Mathematics
    totals = compute_totals(open_df, closed_df)
    total_raw_pnl = totals["total"]
    fmt_losers = force_zero_ending(totals["losers"])
    fmt_winners = force_zero_ending(totals["winners"])

    if midday_risk_activation_due(
        RISK_CANDLE_CONTROL_ENABLED,
        risk_control_activated,
        now_ist().time(),
        RUNEXACPXY_CNTRLRSKBAR_ACTIVATION_TIME,
    ):
        pnl_offset = total_raw_pnl
        historical_peak_record = 0.0
        consecutive_breaches = 0
        risk_control_activated = True
        save_check_state(0)
        print(f"⏱️ {Fore.CYAN}Risk candle activated at 13:15 IST with a fresh P&L baseline.")

    current_game_pnl = total_raw_pnl - pnl_offset
    winners_peak_brick, active_trailing_exit, is_breached = compute_stop(
        current_game_pnl, historical_peak_record, totals["imbalance_factor"])
    active_target_exit = (
        PEAK_CEILING
        if RUNEXACPXY_RISK_MODE == "PEAK"
        else PEAK_CEILING / totals["imbalance_factor"]
    )

    # 6. Telemetry (3-line format)
    print(f"PnL {int(current_game_pnl)} | Pek {int(winners_peak_brick)} | Stp {int(active_trailing_exit)}")
    print(f"Los {fmt_losers} | Win {fmt_winners}")
    acpnl = totals["losers"] + totals["winners"]
    acpnl_label_color = Fore.GREEN if acpnl >= 0 else Fore.RED
    print(f"{acpnl_label_color}└─ ACPNL{Style.RESET_ALL} {int(acpnl)}".rjust(50))

    # 7. Breach handling
    risk_exit_enabled = not RISK_CANDLE_CONTROL_ENABLED or risk_control_activated
    if is_breached and risk_exit_enabled:
        consecutive_breaches += 1
        save_check_state(consecutive_breaches)
        save_session_state(
            winners_peak_brick, current_game_pnl, active_trailing_exit, pnl_offset,
            risk_control_activated=risk_control_activated,
            target_exit_line=active_target_exit,
        )

        if consecutive_breaches >= BREACH_TICKS_REQUIRED:
            sys.stdout.write(f"\n{Fore.RED}{Style.BRIGHT} !! CRITICAL TRADING BREACH DETECTED !! {Style.RESET_ALL}\n")
            sys.stdout.flush()

            if str(RISK_ACTION).upper().strip() != "YES":
                print(f"{Fore.BLUE}{Style.BRIGHT}ℹ️ [PASSIVE ALERT] RISK_ACTION=NO. Would square off everything now.")
            else:
                liquidate_and_exit(
                    client, total_raw_pnl,
                    risk_control_activated=risk_control_activated,
                )     # always ends with sys.exit(...)
    else:
        if consecutive_breaches > 0:
            consecutive_breaches = 0
            save_check_state(0)

    # 8. Final sync (always carries today's timestamp)
    save_session_state(
        winners_peak_brick, current_game_pnl, active_trailing_exit, pnl_offset,
        risk_control_activated=risk_control_activated,
        target_exit_line=active_target_exit,
    )
