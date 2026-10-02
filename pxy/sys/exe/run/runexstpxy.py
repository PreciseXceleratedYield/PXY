#!/usr/bin/env python3
# runexstpxy.py   (lives in ~/pxy/sys/exe/run/)
#
# MASTER RISK LEDGER, part 2 of 6: state files (breach counter, session state, hidden meta),
# the once-a-day stale check and purge. Split out of runexacpxy.py (pure move, no behaviour change).
import os
import sys
from datetime import datetime
from colorama import Fore, Style

from runexiopxy import (
    RENKO_STATE_FILE, CHECK_STATE_FILE, META_FILE, DAILY_LIST_FILES, IST,
    now_ist, today_ist, _atomic_write_json, _read_json_retry,
)
from runexmtpxy import INITIAL_LOSS_FLOOR


# ---------------------------------------------------------------------------
# CHECK STATE (consecutive breach counter)
# ---------------------------------------------------------------------------
def load_check_state():
    """Missing or unreadable JSON -> counter 0. Any other error is raised so the caller skips the tick."""
    try:
        d = _read_json_retry(CHECK_STATE_FILE)
    except FileNotFoundError:
        return {"consecutive_breaches": 0}
    except ValueError as e:     # JSONDecodeError is a ValueError
        print(f"{Fore.YELLOW}⚠️ Breach counter file unreadable ({e}); treating as 0.")
        return {"consecutive_breaches": 0}
    if not isinstance(d, dict):
        print(f"{Fore.YELLOW}⚠️ Breach counter file has unexpected shape; treating as 0.")
        return {"consecutive_breaches": 0}
    try:
        n = max(0, int(d.get("consecutive_breaches", 0)))
    except (TypeError, ValueError):
        n = 0
    return {"consecutive_breaches": n}


def save_check_state(counter):
    return _atomic_write_json(CHECK_STATE_FILE, {
        "consecutive_breaches": int(counter),
        "updated_time": now_ist().strftime("%H:%M:%S"),
    })


# ---------------------------------------------------------------------------
# SESSION STATE (peak / offset / exit line)
# ---------------------------------------------------------------------------
def load_session_state():
    """
    Returns None  -> file does not exist (first run / new day).
    Returns dict  -> parsed state.
    Raises        -> unreadable file. The caller must SKIP the tick, never fall back to zeros.
    """
    try:
        d = _read_json_retry(RENKO_STATE_FILE)
    except FileNotFoundError:
        return None
    if not isinstance(d, dict):
        raise ValueError("session state file is not a JSON object")
    return {
        "session_peak_pnl": float(d.get("session_peak_pnl", 0.0)),
        "current_net_pnl": float(d.get("current_net_pnl", 0.0)),
        "active_exit_line": float(d.get("active_exit_line", INITIAL_LOSS_FLOOR)),
        "pnl_offset": float(d.get("pnl_offset", 0.0)),
        "updated_timestamp": str(d.get("updated_timestamp", "") or ""),
    }


def save_session_state(peak_value, current_net, exit_line, pnl_offset_val):
    return _atomic_write_json(RENKO_STATE_FILE, {
        "session_peak_pnl": float(peak_value),
        "current_net_pnl": float(current_net),
        "active_exit_line": float(exit_line),
        "pnl_offset": float(pnl_offset_val),
        "updated_timestamp": now_ist().strftime("%Y-%m-%d %H:%M:%S"),
    })


# ---------------------------------------------------------------------------
# HIDDEN META (last counted tick + ledger basis)
# ---------------------------------------------------------------------------
def load_meta():
    try:
        d = _read_json_retry(META_FILE)
        if isinstance(d, dict):
            return {
                "last_tick_epoch": float(d.get("last_tick_epoch", 0.0) or 0.0),
                "ledger_basis": d.get("ledger_basis"),
            }
    except Exception:
        pass
    return {"last_tick_epoch": 0.0, "ledger_basis": None}


def save_meta(meta):
    return _atomic_write_json(META_FILE, {
        "last_tick_epoch": float(meta.get("last_tick_epoch", 0.0)),
        "ledger_basis": meta.get("ledger_basis"),
    })


def _find_runlilo_module():
    """The module that is calling us (imported as runlilopxy, run.runlilopxy, or run directly)."""
    for name in ("runlilopxy", "run.runlilopxy", "__main__"):
        m = sys.modules.get(name)
        if m is not None and hasattr(m, "process_lilo_orders"):
            return m
    return None


def _current_filter_time():
    m = _find_runlilo_module()
    val = getattr(m, "FILTER_TIME", None) if m is not None else None
    return None if val is None else str(val)


# ---------------------------------------------------------------------------
# ONCE-A-DAY STALE FILE OVERRIDE
# ---------------------------------------------------------------------------
def state_is_stale(state):
    """True only when there is no state file, or it was last written on an earlier date."""
    if state is None:
        return True
    ts = state.get("updated_timestamp", "")
    if len(ts) >= 10 and ts[4] == "-" and ts[7] == "-":
        stored_date = ts[:10]
    else:
        try:
            stored_date = datetime.fromtimestamp(
                os.path.getmtime(RENKO_STATE_FILE), IST).strftime("%Y-%m-%d")
        except OSError:
            return True
    return stored_date != today_ist()


def purge_stale_cache():
    """Clear yesterday's data and write today's baseline state. Runs once per day."""
    today = today_ist()
    print(f"\n⏰ {Fore.GREEN}{Style.BRIGHT}NEW DAY DETECTED! OVERRIDING STALE WEB JSON CACHE...")

    for path in DAILY_LIST_FILES:
        if not os.path.exists(path):
            continue
        try:
            mdate = datetime.fromtimestamp(os.path.getmtime(path), IST).strftime("%Y-%m-%d")
            if mdate != today:                  # never wipe a file already written today
                _atomic_write_json(path, [])
        except Exception as e:
            print(f"{Fore.YELLOW}⚠️ Could not clear {os.path.basename(path)}: {e}")

    # Writing today's timestamp here is what stops the purge from running again today.
    save_session_state(0.0, 0.0, INITIAL_LOSS_FLOOR, 0.0)
    save_check_state(0)
    save_meta({"last_tick_epoch": 0.0, "ledger_basis": _current_filter_time()})
    print(f"🧹 {Fore.CYAN}Stale cache overridden. Baseline written for {today}.\n")
