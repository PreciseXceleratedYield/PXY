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
from colorama import Fore, Style, init

from runexiopxy import now_ist, today_ist, RENKO_STATE_FILE, WEB_DIR, SQUAREOFF_SCRIPT_PATH  # noqa: F401
from runexmtpxy import (
    INITIAL_LOSS_FLOOR, compute_totals, compute_stop, force_zero_ending, _both_empty,
)
from runexstpxy import (
    load_check_state, save_check_state, load_session_state, save_session_state,
    load_meta, save_meta, state_is_stale, purge_stale_cache, _current_filter_time,
)
from runexlckpxy import _acquire_lock, _release_lock, ledger_busy  # noqa: F401
from runexlqdpxy import liquidate_and_exit, run_squareoff, wait_until_flat  # noqa: F401

init(autoreset=True)

# ==================== CONFIG (this file's settings) ====================
RISK_ACTION = "YES"             # "YES" = square off + sys.exit on a confirmed breach; "NO" = passive (prints and saves state only)
BREACH_TICKS_REQUIRED = 3       # consecutive breached ticks before liquidation
TICK_MIN_GAP_SECONDS = 10       # one tick per cycle: calls closer together than this are skipped (the exit pipe and the avg pipe both load the ledger every cycle)
LEDGER_BASIS_GUARD = True       # if runlilopxy's FILTER_TIME changed since the last tick (ledger restarted after a square-off), start a fresh game instead of subtracting an old offset
VIEW_ONLY_ENV = "PXY_VIEW_ONLY" # set to "1" by manual/viewing runs: they must never advance the breach count
DEBUG_MODE = True               # verbose skip/guard messages (turn off after Monday)
# =======================================================================

# Re-entrancy guard: the post-square-off ledger refresh calls process_lilo_orders again,
# which would call this module again.
_IN_LEDGER = False


def debug_log(msg, color=Fore.BLUE):
    if DEBUG_MODE:
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
    if state_is_stale(state_on_disk):
        purge_stale_cache()
        historical_peak_record = 0.0
        pnl_offset = 0.0
        consecutive_breaches = 0
    else:
        historical_peak_record = state_on_disk["session_peak_pnl"]
        pnl_offset = state_on_disk["pnl_offset"]
        consecutive_breaches = check_state_on_disk["consecutive_breaches"]

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

    current_game_pnl = total_raw_pnl - pnl_offset
    winners_peak_brick, active_trailing_exit, is_breached = compute_stop(
        current_game_pnl, historical_peak_record, totals["open_rows"])

    # 6. Telemetry
    print(f"PnL {int(current_game_pnl)} | Pek {int(winners_peak_brick)} | Stp {int(active_trailing_exit)} | "
          f"Los {fmt_losers} | Win {fmt_winners}")

    # 7. Breach handling
    if is_breached:
        consecutive_breaches += 1
        save_check_state(consecutive_breaches)
        save_session_state(winners_peak_brick, current_game_pnl, active_trailing_exit, pnl_offset)

        if consecutive_breaches >= BREACH_TICKS_REQUIRED:
            sys.stdout.write(f"\n{Fore.RED}{Style.BRIGHT} !! CRITICAL TRADING BREACH DETECTED !! {Style.RESET_ALL}\n")
            sys.stdout.flush()

            if str(RISK_ACTION).upper().strip() != "YES":
                print(f"{Fore.BLUE}{Style.BRIGHT}ℹ️ [PASSIVE ALERT] RISK_ACTION=NO. Would square off everything now.")
            else:
                liquidate_and_exit(client, total_raw_pnl)     # always ends with sys.exit(...)
    else:
        if consecutive_breaches > 0:
            consecutive_breaches = 0
            save_check_state(0)

    # 8. Final sync (always carries today's timestamp)
    save_session_state(winners_peak_brick, current_game_pnl, active_trailing_exit, pnl_offset)
