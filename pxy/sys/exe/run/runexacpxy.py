#!/usr/bin/env python3
# runexacpxy.py   (lives in ~/pxy/sys/exe/run/)
#
# MASTER RISK LEDGER orchestrator: cycle premium-profit target.
# Called from runlilopxy.process_lilo_orders (two hooks, see README_risk.md):
#   1) runexacpxy.daily_purge_check()                             top of process_lilo_orders
#   2) runexacpxy.execute_master_risk_ledger(client, open_df, closed_df)   after open_df / closed_df exist
#
# On a confirmed target it submits square-off orders and persists a pending state.
# Later broker snapshots confirm flatness before risk state is reset; the engine keeps running.
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
    RUNEXACPXY_TARGET_START,
    RUNEXACPXY_TARGET_END,
    RUNEXACPXY_TARGET_OPEN_RUPEES,
    RUNEXACPXY_TARGET_CLOSED_RUPEES,
    RUNEXACPXY_BREACH_TICKS_REQUIRED,
    RUNEXACPXY_CYCLE_TARGET_PCT,
    RUNEXACPXY_DEBUG_ENABLED,
    RUNEXACPXY_LEDGER_BASIS_GUARD,
    RUNEXACPXY_LATE_DAY_END,
    RUNEXACPXY_LATE_DAY_START,
    RUNEXACPXY_LATE_DAY_TARGET_PCT,
    RUNEXACPXY_TARGET_SQUAREOFF_ENABLED,
    RUNEXACPXY_TICK_MIN_GAP_SECONDS,
    RUNEXACPXY_VIEW_ONLY_ENV,
)
from runexiopxy import now_ist, today_ist, RENKO_STATE_FILE, WEB_DIR, SQUAREOFF_SCRIPT_PATH  # noqa: F401
from runexmtpxy import (
    INITIAL_RISK_BAR_TARGET, compute_totals,
    cycle_closed_snapshot, cycle_ledger_tags, cycle_risk_metrics,
    cycle_start_time,
)
from runexstpxy import (
    load_check_state, save_check_state, load_session_state, save_session_state,
    load_meta, save_meta, state_is_stale, purge_stale_cache, _current_filter_time,
)
from runexlckpxy import _acquire_lock, _release_lock, ledger_busy  # noqa: F401
from runexlqdpxy import (
    broker_positions_flat, liquidate_and_exit, has_working_sell_orders,
    run_squareoff,
)  # noqa: F401

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


def riskbar_minute_target(now=None):
    """Absolute RiskBar P&L target, stepped once per whole IST minute."""
    current = now if now is not None else now_ist()
    minute = current.hour * 60 + current.minute
    start = RUNEXACPXY_TARGET_START.hour * 60 + RUNEXACPXY_TARGET_START.minute
    end = RUNEXACPXY_TARGET_END.hour * 60 + RUNEXACPXY_TARGET_END.minute
    if not start <= minute <= end:
        return RUNEXACPXY_TARGET_CLOSED_RUPEES
    return RUNEXACPXY_TARGET_OPEN_RUPEES * (end - minute) / (end - start)


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
    """Defensive gatekeeper. Returns normally when idle, skipped, or liquidating asynchronously.
    A persisted pending state blocks new trading until a later broker snapshot confirms flatness."""
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
    liquidation_is_pending = bool(
        state_on_disk and state_on_disk.get("liquidation_pending", False)
    )
    session_state_is_stale = (
        state_is_stale(state_on_disk) and not liquidation_is_pending
    )
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
    closed_cycle_count = (
        0 if session_state_is_stale
        else int(state_on_disk.get("closed_cycle_count", 0))
    )
    last_closed_snapshot = (
        None if session_state_is_stale
        else state_on_disk.get("last_closed_snapshot")
    )
    last_closed_cycle_id = (
        "" if session_state_is_stale
        else state_on_disk.get("last_closed_cycle_id", "")
    )
    closed_cycles = (
        [] if session_state_is_stale
        else list(state_on_disk.get("closed_cycles", []))
    )
    if not closed_cycles and last_closed_snapshot and closed_cycle_count:
        legacy_snapshot = dict(last_closed_snapshot)
        legacy_snapshot.setdefault("cycle_id", closed_cycle_count)
        legacy_snapshot.setdefault(
            "cycle_tags",
            sorted({
                str(position.get("tag", "")).strip()
                for position in legacy_snapshot.get("positions", [])
                if str(position.get("tag", "")).strip()
            }),
        )
        closed_cycles.append(legacy_snapshot)
    # 3. One tick per cycle: the exit pipe and the avg pipe both load the ledger every cycle.
    meta = load_meta()
    now_epoch = time.time()
    if TICK_MIN_GAP_SECONDS > 0 and (now_epoch - meta["last_tick_epoch"]) < TICK_MIN_GAP_SECONDS:
        debug_log(f"Tick skipped: previous tick {now_epoch - meta['last_tick_epoch']:.1f}s ago "
                  f"(< {TICK_MIN_GAP_SECONDS}s).")
        return

    # An initiated liquidation stays authoritative across cycles and engine restarts.
    # A fresh broker snapshot, not order acceptance, decides when the cycle is flat.
    if liquidation_is_pending:
        meta["last_tick_epoch"] = now_epoch
        save_meta(meta)
        current_total = compute_totals(open_df, closed_df)["total"]
        pending_risk_state = dict(state_on_disk)
        pending_risk_state["cycle_tags"] = state_on_disk.get("active_cycle_tags", [])
        pending_risk_state["cycle_started_at"] = state_on_disk.get("active_cycle_started_at")
        if broker_positions_flat(client):
            if closed_df is None or closed_df.empty:
                print(
                    f"{Fore.YELLOW}⚠️ Broker positions are flat, but LILO has no completed "
                    "trade rows to reconcile; risk reset remains pending."
                )
                return
            active_tags = {
                str(tag).strip()
                for tag in state_on_disk.get("active_cycle_tags", [])
                if str(tag).strip()
            }
            closed_columns = {
                str(column).upper(): column for column in closed_df.columns
            }
            tag_column = closed_columns.get("TAG")
            closed_tags = (
                {
                    str(tag).strip()
                    for tag in closed_df[tag_column]
                    if str(tag).strip()
                }
                if tag_column is not None else set()
            )
            if active_tags and not active_tags.issubset(closed_tags):
                print(
                    f"{Fore.YELLOW}⚠️ Broker is flat, but LILO has not reconciled every "
                    "active risk-cycle tag; risk reset remains pending."
                )
                return
            if has_working_sell_orders(client):
                print(
                    f"{Fore.YELLOW}⏳ Broker positions are flat, but a sell order is still working; "
                    "risk reset remains pending."
                )
                return
            liquidate_and_exit(
                client,
                current_total,
                risk_control_activated=True,
                risk_state=pending_risk_state,
                broker_flat_confirmed=True,
            )
        else:
            liquidate_and_exit(
                client,
                current_total,
                risk_control_activated=True,
                risk_state=pending_risk_state,
            )
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

    # The portfolio must be completely flat before a cycle is closed or reset.
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
            snapshot = cycle_closed_snapshot(
                closed_df, previous_tags, previous_start
            )
            if snapshot is not None:
                booked_profit += snapshot["realized_pnl"]
                closed_cycle_count += 1
                snapshot["cycle_id"] = closed_cycle_count
                closed_cycles.append(snapshot)
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
            closed_cycle_count=closed_cycle_count,
            last_closed_snapshot=last_closed_snapshot,
            last_closed_cycle_id=last_closed_cycle_id,
            closed_cycles=closed_cycles,
            active_cycle_id=None,
            active_cycle_tags=[],
            active_cycle_started_at=None,
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
            "keeping the cycle open and skipping cycle accounting."
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
            "baseline continues until the full cycle is flat."
        )
    else:
        cycle_tags = previous_tags | open_tags

    meta["risk_cycle_started_at"] = cycle_started_at
    meta["risk_cycle_tags"] = sorted(cycle_tags)
    meta["last_tick_epoch"] = now_epoch
    save_meta(meta)

    totals = compute_totals(open_df, closed_df)
    total_raw_pnl = totals["total"]
    current_time = now_ist().time()

    metrics = cycle_risk_metrics(
        open_df,
        closed_df,
        cycle_tags,
        exit_signal,
    )
    # Shared metrics calculate the cycle target; OUT direction does not gate RiskBar.
    book_count = metrics["cycle_trade_count"]
    risk_target = metrics["target"]
    # Pending liquidations resume earlier in _tick regardless of signal.
    # New RiskBar liquidations can start regardless of OUT signal.
    risk_enabled = (
        RISK_CANDLE_CONTROL_ENABLED
        and RUNEXACPXY_TARGET_SQUAREOFF_ENABLED
        and metrics["both_sides_open"]
    )
    active_cycle_id = closed_cycle_count + 1
    print(format_cycle_status(active_cycle_id, risk_target))
    # Explain a displayed profit breach that cannot initiate a RiskBar exit.
    # Diagnostic only: no changes to order execution or liquidation gates.
    if metrics["cycle_pnl"] >= risk_target and not metrics["target_reached"]:
        reasons = []
        if not RISK_CANDLE_CONTROL_ENABLED:
            reasons.append("controller disabled")
        if not RUNEXACPXY_TARGET_SQUAREOFF_ENABLED:
            reasons.append("target square-off disabled")
        if not metrics["both_sides_open"]:
            reasons.append("both CE and PE must be open")
        if not metrics["both_sides_negative"]:
            reasons.append("both open sides must have negative P&L percentages")
        if metrics["premium_paid"] <= 0:
            reasons.append("cycle premium missing")
        if metrics["cycle_trade_count"] <= 0:
            reasons.append("no matched cycle trade rows")
        print(
            f"{Fore.YELLOW}⚠️ RiskBar target displayed but exit ineligible: "
            f"cycle_pnl=₹{metrics['cycle_pnl']:.2f}, "
            f"target=₹{risk_target:.2f}, "
            f"premium=₹{metrics['premium_paid']:.2f}, "
            f"signal={exit_signal}, reasons={', '.join(reasons) or 'unresolved'}"
        )
    elif metrics["cycle_pnl"] >= risk_target and not risk_enabled:
        print(
            f"{Fore.YELLOW}⚠️ RiskBar target reached but controller inactive: "
            f"cycle_pnl=₹{metrics['cycle_pnl']:.2f}, target=₹{risk_target:.2f}, "
            f"both_sides_open={metrics['both_sides_open']}, "
            f"controller={RISK_CANDLE_CONTROL_ENABLED}, "
            f"target_squareoff={RUNEXACPXY_TARGET_SQUAREOFF_ENABLED}"
        )

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
            closed_cycle_count=closed_cycle_count,
            last_closed_snapshot=last_closed_snapshot,
            last_closed_cycle_id=last_closed_cycle_id,
            closed_cycles=closed_cycles,
            active_cycle_id=active_cycle_id,
            active_cycle_tags=sorted(cycle_tags),
            active_cycle_started_at=cycle_started_at,
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
            closed_cycle_count=closed_cycle_count,
            last_closed_snapshot=last_closed_snapshot,
            last_closed_cycle_id=last_closed_cycle_id,
            closed_cycles=closed_cycles,
            active_cycle_id=active_cycle_id,
            active_cycle_tags=sorted(cycle_tags),
            active_cycle_started_at=cycle_started_at,
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
        closed_cycle_count=closed_cycle_count,
        last_closed_snapshot=last_closed_snapshot,
        last_closed_cycle_id=last_closed_cycle_id,
        closed_cycles=closed_cycles,
        active_cycle_id=active_cycle_id,
        active_cycle_tags=sorted(cycle_tags),
        active_cycle_started_at=cycle_started_at,
    )
    print(
        f"{Fore.YELLOW}⚠️ {str(exit_signal).upper().strip()} cycle profit target reached "
        f"({metrics['target_pct']:.2f}% of ₹{metrics['premium_paid']:.2f} invested "
        f"across {book_count} present-cycle rows; minimum ₹{metrics['minimum_pnl']:.2f}) "
        f"(confirmation {consecutive_breaches}/{BREACH_TICKS_REQUIRED})."
    )
    if consecutive_breaches < BREACH_TICKS_REQUIRED:
        return

    pending_saved = save_session_state(
        0.0,
        metrics["cycle_pnl"],
        -risk_target,
        pnl_offset,
        risk_control_activated=True,
        target_exit_line=risk_target,
        booked_profit=booked_profit,
        closed_cycle_count=closed_cycle_count,
        last_closed_snapshot=last_closed_snapshot,
        last_closed_cycle_id=last_closed_cycle_id,
        closed_cycles=closed_cycles,
        active_cycle_id=active_cycle_id,
        active_cycle_tags=sorted(cycle_tags),
        active_cycle_started_at=cycle_started_at,
        liquidation_pending=True,
    )
    if not pending_saved:
        print(f"{Fore.RED}⚠️ Could not persist pending liquidation state; square-off not submitted.")
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
            "closed_cycle_count": closed_cycle_count,
            "last_closed_snapshot": last_closed_snapshot,
            "last_closed_cycle_id": last_closed_cycle_id,
            "closed_cycles": closed_cycles,
            "cycle_tags": sorted(cycle_tags),
            "cycle_started_at": cycle_started_at,
        },
    )


def format_cycle_status(cycle_number, target):
    """Return the single fixed-width status line for the currently open cycle."""
    return f"CYCLE{cycle_number} OPEN - WAIT TARGET RS {target:.0f}"[:40].ljust(40)


