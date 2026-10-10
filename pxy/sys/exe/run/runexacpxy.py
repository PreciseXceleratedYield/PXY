#!/usr/bin/env python3
# runexacpxy.py   (lives in ~/pxy/sys/exe/run/)
#
# MASTER RISK LEDGER orchestrator: cycle premium-profit target.
# Called from runlilopxy.process_lilo_orders (two hooks, see README_risk.md):
#   1) runexacpxy.daily_purge_check()                             top of process_lilo_orders
#   2) runexacpxy.execute_master_risk_ledger(client, open_df, closed_df)   after open_df / closed_df exist
#
# On a confirmed target it squares off everything, waits until the broker is flat,
# resets risk state and ends the process with sys.exit(...).
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
    RUNEXACPXY_BREACH_TICKS_REQUIRED,
    RUNEXACPXY_CYCLE_TARGET_PCT,
    RUNEXACPXY_DEBUG_ENABLED,
    RUNEXACPXY_LEDGER_BASIS_GUARD,
    RUNEXACPXY_TARGET_SQUAREOFF_ENABLED,
    RUNEXACPXY_TICK_MIN_GAP_SECONDS,
    RUNEXACPXY_VIEW_ONLY_ENV,
)
from runexiopxy import now_ist, today_ist, RENKO_STATE_FILE, WEB_DIR, SQUAREOFF_SCRIPT_PATH  # noqa: F401
from runexmtpxy import (
    INITIAL_RISK_BAR_TARGET, compute_totals,
    cycle_closed_book_snapshot, cycle_ledger_tags, cycle_risk_metrics,
    cycle_start_time,
)
from runexstpxy import (
    load_check_state, save_check_state, load_session_state, save_session_state,
    load_meta, save_meta, state_is_stale, purge_stale_cache, _current_filter_time,
)
from runexlckpxy import _acquire_lock, _release_lock, ledger_busy  # noqa: F401
from runexlqdpxy import liquidate_and_exit, run_squareoff, wait_until_flat  # noqa: F401

init(autoreset=True)

# ==================== CONFIG (this file's settings) ====================
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
def execute_master_risk_ledger(client, open_df, closed_df, exit_signal=None):
    """Defensive gatekeeper. Returns normally when there is nothing to do or the tick was skipped.
    On a confirmed breach: square-off, flat check, state reset, then sys.exit(...)."""
    global _IN_LEDGER
    if _IN_LEDGER:
        return
    if os.environ.get(VIEW_ONLY_ENV) == "1":
        debug_log("Ledger guard: view-only run; no tick counted.")
        return
    can_run, lock_handle = _acquire_lock()
    if not can_run:
        debug_log("Ledger guard: another tick is running; skipping.")
        return

    _IN_LEDGER = True
    try:
        _tick(client, open_df, closed_df, exit_signal)
    except SystemExit:
        raise
    except Exception as e:
        print(f"{Fore.RED}⚠️ Master risk ledger error (tick skipped, ledger still returned): {e}")
    finally:
        _IN_LEDGER = False
        _release_lock(lock_handle)


def _tick(client, open_df, closed_df, exit_signal=None):
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
        consecutive_breaches = 0
        pnl_offset = 0.0
    else:
        consecutive_breaches = check_state_on_disk["consecutive_breaches"]
        pnl_offset = state_on_disk.get("pnl_offset", 0.0)

    booked_profit = (
        0.0 if session_state_is_stale
        else float(state_on_disk.get("booked_profit", 0.0))
    )
    closed_book_count = (
        0 if session_state_is_stale
        else int(state_on_disk.get("closed_book_count", 0))
    )
    last_closed_snapshot = (
        None if session_state_is_stale
        else state_on_disk.get("last_closed_snapshot")
    )
    last_closed_cycle_id = (
        "" if session_state_is_stale
        else state_on_disk.get("last_closed_cycle_id", "")
    )

    # 3. One tick per cycle: the exit pipe and the avg pipe both load the ledger every cycle.
    meta = load_meta()
    now_epoch = time.time()
    if TICK_MIN_GAP_SECONDS > 0 and (now_epoch - meta["last_tick_epoch"]) < TICK_MIN_GAP_SECONDS:
        debug_log(f"Tick skipped: previous tick {now_epoch - meta['last_tick_epoch']:.1f}s ago "
                  f"(< {TICK_MIN_GAP_SECONDS}s).")
        return

    # 4. Keep the cycle ledger independent of LILO's display/filter basis.
    current_basis = _current_filter_time()
    if LEDGER_BASIS_GUARD and current_basis is not None:
        stored_basis = meta.get("ledger_basis")
        if stored_basis is not None and stored_basis != current_basis:
            print(
                f"🔄 {Fore.CYAN}Ledger start changed ({stored_basis} -> "
                f"{current_basis}); preserving the active risk cycle."
            )
        meta["ledger_basis"] = current_basis

    # The portfolio must be completely flat before a book is closed or reset.
    open_tags = cycle_ledger_tags(open_df)
    portfolio_is_flat = open_df is None or open_df.empty
    if portfolio_is_flat:
        previous_tags = {
            str(tag) for tag in meta.get("risk_cycle_tags", [])
        }
        previous_start = meta.get("risk_cycle_started_at")
        cycle_id = (
            f"{previous_start}|{'|'.join(sorted(previous_tags))}"
            if previous_start and previous_tags else ""
        )
        if cycle_id and cycle_id != last_closed_cycle_id:
            snapshot = cycle_closed_book_snapshot(
                closed_df, previous_tags, previous_start
            )
            if snapshot is not None:
                booked_profit += snapshot["realized_pnl"]
                closed_book_count += 1
                last_closed_snapshot = snapshot
                last_closed_cycle_id = cycle_id

        target_line = INITIAL_RISK_BAR_TARGET
        state_saved = save_session_state(
            0.0,
            0.0,
            -target_line,
            pnl_offset,
            target_exit_line=target_line,
            booked_profit=booked_profit,
            closed_book_count=closed_book_count,
            last_closed_snapshot=last_closed_snapshot,
            last_closed_cycle_id=last_closed_cycle_id,
        )
        if not state_saved:
            return
        meta["risk_cycle_started_at"] = None
        meta["risk_cycle_tags"] = []
        meta["last_tick_epoch"] = now_epoch
        save_meta(meta)
        if consecutive_breaches:
            save_check_state(0)
        return

    open_columns = {str(column).upper(): column for column in open_df.columns}
    tag_column = open_columns.get("TAG")
    if tag_column is None or any(
        str(tag).strip().lower() in {"", "nan", "none", "null"}
        for tag in open_df[tag_column]
    ):
        print(
            f"{Fore.YELLOW}⚠️ Active positions do not all have valid order tags; "
            "keeping the book open and skipping cycle accounting."
        )
        return

    previous_tags = {
        str(tag) for tag in meta.get("risk_cycle_tags", [])
    }
    cycle_started_at = meta.get("risk_cycle_started_at")
    if not cycle_started_at or not previous_tags:
        cycle_started_at = cycle_start_time(open_df)
        if cycle_started_at is None:
            print(
                f"{Fore.YELLOW}⚠️ Risk cycle cannot start: active orders have "
                "no valid buy timestamp; risk check skipped."
            )
            return
        cycle_tags = open_tags
        consecutive_breaches = 0
        save_check_state(0)
        print(
            f"🛡️ {Fore.CYAN}Risk cycle started at {cycle_started_at}; "
            "baseline continues until the full book is flat."
        )
    else:
        cycle_tags = previous_tags | open_tags

    meta["risk_cycle_started_at"] = cycle_started_at
    meta["risk_cycle_tags"] = sorted(cycle_tags)
    meta["last_tick_epoch"] = now_epoch
    save_meta(meta)

    totals = compute_totals(open_df, closed_df)
    total_raw_pnl = totals["total"]
    metrics = cycle_risk_metrics(
        open_df,
        closed_df,
        cycle_tags,
        exit_signal,
        RUNEXACPXY_CYCLE_TARGET_PCT,
    )
    risk_target = (
        metrics["target"] if metrics["both_sides_open"]
        else INITIAL_RISK_BAR_TARGET
    )
    target_label = (
        f"{RUNEXACPXY_CYCLE_TARGET_PCT:.1f}%"
        if metrics["both_sides_open"] else "INITIAL"
    )
    risk_enabled = (
        RISK_CANDLE_CONTROL_ENABLED
        and RUNEXACPXY_TARGET_SQUAREOFF_ENABLED
    )
    print(
        f"🛡️ CYCLE PNL ₹{metrics['cycle_pnl']:.0f} / "
        f"PAID ₹{metrics['premium_paid']:.0f} | "
        f"TARGET {target_label} "
        f"(₹{risk_target:.0f}) | "
        f"OPEN CE/PE {metrics['ce_qty']:.0f}/{metrics['pe_qty']:.0f} | "
        f"HEAVY {metrics['heavy_side'] or 'NONE'} | EXIT {exit_signal or 'NONE'}"
    )
    if not metrics["both_sides_open"]:
        print(
            "🛡️ Waiting for both CE and PE sides; the initial ±₹1,000 lines "
            "are display-only."
        )
    elif metrics["heavy_side_aligned"]:
        print("🛡️ Heavy invested side agrees with exit signal; cycle remains active.")
    else:
        print("🛡️ Heavy side is not aligned; cycle profit target can square off the book.")

    if not risk_enabled:
        if consecutive_breaches:
            save_check_state(0)
        save_session_state(
            0.0,
            metrics["cycle_pnl"],
            -risk_target,
            pnl_offset,
            risk_control_activated=False,
            target_exit_line=risk_target,
            booked_profit=booked_profit,
            closed_book_count=closed_book_count,
            last_closed_snapshot=last_closed_snapshot,
            last_closed_cycle_id=last_closed_cycle_id,
        )
        return

    if not metrics["target_reached"]:
        if consecutive_breaches:
            consecutive_breaches = 0
            save_check_state(0)
        save_session_state(
            0.0,
            metrics["cycle_pnl"],
            -risk_target,
            pnl_offset,
            risk_control_activated=True,
            target_exit_line=risk_target,
            booked_profit=booked_profit,
            closed_book_count=closed_book_count,
            last_closed_snapshot=last_closed_snapshot,
            last_closed_cycle_id=last_closed_cycle_id,
        )
        return

    consecutive_breaches += 1
    save_check_state(consecutive_breaches)
    save_session_state(
        0.0,
        metrics["cycle_pnl"],
        -risk_target,
        pnl_offset,
        risk_control_activated=True,
        target_exit_line=risk_target,
        booked_profit=booked_profit,
        closed_book_count=closed_book_count,
        last_closed_snapshot=last_closed_snapshot,
        last_closed_cycle_id=last_closed_cycle_id,
    )
    print(
        f"{Fore.YELLOW}⚠️ Cycle profit target reached while heavy side is unaligned "
        f"({RUNEXACPXY_CYCLE_TARGET_PCT:.1f}%) "
        f"(confirmation {consecutive_breaches}/{BREACH_TICKS_REQUIRED})."
    )
    if consecutive_breaches < BREACH_TICKS_REQUIRED:
        return

    sys.stdout.write(
        f"\n{Fore.RED}{Style.BRIGHT} !! CYCLE PROFIT TARGET REACHED !! "
        f"{Style.RESET_ALL}\n"
    )
    sys.stdout.flush()
    liquidate_and_exit(
        client,
        total_raw_pnl,
        risk_control_activated=True,
        risk_state={
            "active_target_line": risk_target,
            "booked_profit": booked_profit,
            "closed_book_count": closed_book_count,
            "last_closed_snapshot": last_closed_snapshot,
            "last_closed_cycle_id": last_closed_cycle_id,
            "cycle_tags": sorted(cycle_tags),
            "cycle_started_at": cycle_started_at,
        },
    )
