#!/usr/bin/env python3
# exeexacpxy.py  (hardened version)
import os
import json
import sys
import time
import subprocess
import pytz
import pandas as pd
from datetime import datetime
from pathlib import Path
from colorama import Fore, Style, init

try:
    import fcntl            # Linux / macOS / Termux
except ImportError:         # Windows: run without the overlap lock
    fcntl = None

init(autoreset=True)

# ---------------------------------------------------------------------------
# PATHS
# ---------------------------------------------------------------------------
current_dir = os.path.dirname(os.path.abspath(__file__))
run_dir = os.path.join(current_dir, "run")
for _p in (current_dir, run_dir):
    if _p not in sys.path:
        sys.path.append(_p)

HOME_DIR = str(Path.home())
WEB_DIR = os.path.join(HOME_DIR, "pxy/web")

PNL_JSON_PATH      = os.path.abspath(os.path.join(WEB_DIR, "webpnlpxy.json"))
POS_JSON_PATH      = os.path.abspath(os.path.join(WEB_DIR, "webpospxy.json"))
SQUAREOFF_LOG_FILE = os.path.abspath(os.path.join(WEB_DIR, "websqrpxy.json"))
RENKO_STATE_FILE   = os.path.abspath(os.path.join(WEB_DIR, "webrinkopxy.json"))
CHECK_STATE_FILE   = os.path.abspath(os.path.join(WEB_DIR, "webrnkchkpxy.json"))
LOCK_FILE          = os.path.abspath(os.path.join(WEB_DIR, ".exeexacpxy.lock"))

# Files that hold a JSON list and are cleared once per day
DAILY_LIST_FILES = [PNL_JSON_PATH, POS_JSON_PATH, SQUAREOFF_LOG_FILE]

IST = pytz.timezone("Asia/Kolkata")

# ---------------------------------------------------------------------------
# STRATEGY CONSTANTS (unchanged logic)
# ---------------------------------------------------------------------------
BRICK_SIZE = 140.0
INITIAL_LOSS_FLOOR = -1400.0
LET_GO_BASE = 0.50           # base give-back of peak
LET_GO_STEP = 0.05           # tighten per extra open row
MIN_DROP_GAP = 210.0         # 1.5 bricks
BREACH_TICKS_REQUIRED = 3

# ---------------------------------------------------------------------------
# OPERATIONAL CONSTANTS
# ---------------------------------------------------------------------------
FLAT_CONFIRM_TIMEOUT_SECONDS = 10.0
FLAT_CONFIRM_POLL_SECONDS = 2.0
SQUAREOFF_TIMEOUT_SECONDS = 120
READ_RETRIES = 3
READ_RETRY_DELAY = 0.3


# ---------------------------------------------------------------------------
# TIME HELPERS
# ---------------------------------------------------------------------------
def now_ist():
    return datetime.now(IST)


def today_ist():
    return now_ist().strftime("%Y-%m-%d")


# ---------------------------------------------------------------------------
# SAFE FILE IO
# ---------------------------------------------------------------------------
def _atomic_write_json(path, payload, retries=2):
    """Write to a temp file, fsync, then os.replace. Readers never see a half file."""
    tmp = path + ".tmp"
    last_err = None
    for _ in range(retries + 1):
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(tmp, "w") as f:
                json.dump(payload, f, indent=4)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, path)
            return True
        except Exception as e:
            last_err = e
            time.sleep(0.2)
    print(f"{Fore.RED}⚠️ Write failed for {os.path.basename(path)}: {last_err}")
    return False


def _read_json_retry(path):
    """Read JSON, retrying briefly. FileNotFoundError is raised immediately."""
    last_err = None
    for attempt in range(READ_RETRIES):
        try:
            with open(path, "r") as f:
                return json.load(f)
        except FileNotFoundError:
            raise
        except Exception as e:
            last_err = e
            if attempt < READ_RETRIES - 1:
                time.sleep(READ_RETRY_DELAY)
    raise last_err


# ---------------------------------------------------------------------------
# CHECK STATE (consecutive breach counter)
# ---------------------------------------------------------------------------
def load_check_state():
    """
    Missing file or unreadable JSON -> counter 0 (non-critical, self-heals on next write).
    Any other error (permissions, IO) is raised so the caller skips the tick.
    """
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
    Raises        -> unreadable file. Caller must SKIP the tick, never fall back to zeros.
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
# ONCE-A-DAY STALE FILE OVERRIDE
# ---------------------------------------------------------------------------
def state_is_stale(state):
    """
    True only when there is no state file, or it was last written on an earlier date.
    A state file without a timestamp (older script version) falls back to its mtime
    date, so deploying this version mid-day does not wipe today's peak.
    """
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
    print(f"🧹 {Fore.CYAN}Stale cache overridden. Baseline written for {today}.\n")


# ---------------------------------------------------------------------------
# BROKER HELPERS
# ---------------------------------------------------------------------------
def broker_positions_flat(client):
    try:
        def _num(v):
            return float(str(v).replace(",", "").strip() or 0)

        res = client.positions()
        if isinstance(res, dict):
            data = res.get("data")
            if isinstance(data, list):
                for pos in data:
                    net_qty = _num(pos.get("net_qty", 0))
                    if net_qty == 0:
                        net_qty = _num(pos.get("flBuyQty", 0)) - _num(pos.get("flSellQty", 0))
                    if abs(net_qty) > 0:
                        return False
                return True
            if "no data" in str(res.get("errMsg", "") or res.get("message", "")).lower():
                return True
        return False
    except Exception:
        return False


def wait_until_flat(client):
    """Poll the broker until flat or timeout, so slow fills don't cause a false 'not flat'."""
    deadline = time.time() + FLAT_CONFIRM_TIMEOUT_SECONDS
    while True:
        if broker_positions_flat(client):
            return True
        if time.time() >= deadline:
            return False
        time.sleep(FLAT_CONFIRM_POLL_SECONDS)


def run_squareoff():
    script_path = os.path.join(current_dir, "exesqrpxy.py")
    if not os.path.exists(script_path):
        print(f"{Fore.RED}❌ Square-off script not found: {script_path}")
        return False
    python_executable = sys.executable if sys.executable else "python"
    try:
        result = subprocess.run([python_executable, script_path, "-all"],
                                timeout=SQUAREOFF_TIMEOUT_SECONDS)
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        print(f"{Fore.RED}❌ Square-off script timed out after {SQUAREOFF_TIMEOUT_SECONDS}s.")
        return False
    except Exception as e:
        print(f"{Fore.RED}❌ Square-off script failed to run: {e}")
        return False


# ---------------------------------------------------------------------------
# LEDGER MATH
# ---------------------------------------------------------------------------
def _prep_frame(df):
    """Handle None, upper-case headers, pad missing columns, force numeric."""
    df = pd.DataFrame() if df is None else df.copy()
    df.columns = [str(c).upper() for c in df.columns]
    for col in ("BUY_PRC", "SELL_PRC", "PNL"):
        if col not in df.columns:
            df[col] = 0.0
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
    return df


def _both_empty(open_df, closed_df):
    return ((open_df is None or open_df.empty) and
            (closed_df is None or closed_df.empty))


def compute_totals(open_df, closed_df):
    df_open = _prep_frame(open_df)
    df_closed = _prep_frame(closed_df)

    win_open = df_open[df_open["BUY_PRC"] < df_open["SELL_PRC"]]
    win_closed = df_closed[df_closed["BUY_PRC"] < df_closed["SELL_PRC"]]

    total = float(df_open["PNL"].sum() + df_closed["PNL"].sum())
    winners = float(win_open["PNL"].sum() + win_closed["PNL"].sum())
    return {
        "total": total,
        "winners": winners,
        "losers": total - winners,
        "open_rows": len(df_open),
    }


def force_zero_ending(val):
    return int(round(val / 10.0) * 10)


# ---------------------------------------------------------------------------
# OVERLAP LOCK (two ticks must never run at the same time)
# ---------------------------------------------------------------------------
def acquire_run_lock():
    """Returns (can_run, handle)."""
    if fcntl is None:
        return True, None
    try:
        os.makedirs(os.path.dirname(LOCK_FILE), exist_ok=True)
        fh = open(LOCK_FILE, "w")
    except OSError as e:
        print(f"{Fore.YELLOW}⚠️ Lock file unavailable ({e}); running without overlap lock.")
        return True, None
    try:
        fcntl.flock(fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return True, fh
    except OSError:
        fh.close()
        return False, None


# ---------------------------------------------------------------------------
# MAIN TICK
# ---------------------------------------------------------------------------
def pipe_master_execution_ledger():
    can_run, lock_handle = acquire_run_lock()
    if not can_run:
        print(f"ℹ️ {Fore.YELLOW}Previous tick still running. Skipping this tick.")
        return
    try:
        _run_tick()
    finally:
        if lock_handle:
            try:
                fcntl.flock(lock_handle, fcntl.LOCK_UN)
                lock_handle.close()
            except Exception:
                pass


def _run_tick():
    # 1. Broker + ledger. Any failure skips the tick without touching state.
    try:
        from run.runclntpxy import get_session
        from run import runlilopxy
        client = get_session()
    except Exception as e:
        print(f"{Fore.RED}❌ Broker session error: {e}")
        return
    if not client:
        print(f"{Fore.RED}❌ Failed to establish broker session client.")
        return

    try:
        open_df, closed_df = runlilopxy.process_lilo_orders(client)
    except Exception as e:
        print(f"{Fore.RED}❌ Ledger fetch error: {e}. Skipping tick, state untouched.")
        return

    # 2. Data guard: empty tick touches nothing (no purge, no save).
    if _both_empty(open_df, closed_df):
        print(f"ℹ️ {Fore.YELLOW}No active market data found. Retaining current web cache parameters...")
        return

    # 3. Read state. A corrupt/locked file skips the tick rather than writing zeros.
    try:
        state_on_disk = load_session_state()
        check_state_on_disk = load_check_state()
    except Exception as e:
        print(f"{Fore.RED}⚠️ State file unreadable: {e}. Skipping tick. "
              f"If this repeats, fix or delete {RENKO_STATE_FILE}.")
        return

    # 4. Once-a-day override. Only a missing file or an earlier date counts as stale.
    if state_is_stale(state_on_disk):
        purge_stale_cache()
        historical_peak_record = 0.0
        pnl_offset = 0.0
        consecutive_breaches = 0
    else:
        historical_peak_record = state_on_disk["session_peak_pnl"]
        pnl_offset = state_on_disk["pnl_offset"]
        consecutive_breaches = check_state_on_disk["consecutive_breaches"]

    # 5. Mathematics
    totals = compute_totals(open_df, closed_df)
    total_raw_pnl = totals["total"]
    fmt_losers = force_zero_ending(totals["losers"])
    fmt_winners = force_zero_ending(totals["winners"])

    current_game_pnl = total_raw_pnl - pnl_offset

    completed_bricks = int(current_game_pnl // BRICK_SIZE)
    calculated_live_peak = float(completed_bricks * BRICK_SIZE)

    # Peak only moves up within a game
    winners_peak_brick = max(calculated_live_peak, historical_peak_record)

    extra_rows = max(0, totals["open_rows"] - 1)
    let_go_percentage = max(0.0, LET_GO_BASE - extra_rows * LET_GO_STEP)
    final_drop_gap = max(MIN_DROP_GAP, winners_peak_brick * let_go_percentage)

    if winners_peak_brick > 0:
        active_trailing_exit = winners_peak_brick - final_drop_gap
    else:
        active_trailing_exit = INITIAL_LOSS_FLOOR

    is_breached = current_game_pnl <= INITIAL_LOSS_FLOOR
    if not is_breached and winners_peak_brick > 0:
        is_breached = current_game_pnl <= active_trailing_exit

    # 6. Telemetry
    print(f"\nLos: {fmt_losers:<13} | {fmt_winners:>13}: Win")
    print(f"               Stp: | {int(active_trailing_exit):<13}")
    print(f"PnL: {int(current_game_pnl):<13} | {int(winners_peak_brick):>13}: Pek\n")

    # 7. Breach handling
    if is_breached:
        consecutive_breaches += 1
        save_check_state(consecutive_breaches)
        save_session_state(winners_peak_brick, current_game_pnl, active_trailing_exit, pnl_offset)

        if consecutive_breaches >= BREACH_TICKS_REQUIRED:
            sys.stdout.write(f"\n{Fore.RED}{Style.BRIGHT} !! CRITICAL TRADING BREACH DETECTED !! {Style.RESET_ALL}\n")
            sys.stdout.flush()

            run_squareoff()

            # Flat is decided by the broker, not by the script's exit code.
            if wait_until_flat(client):
                # Re-pull the ledger so the offset includes the square-off fills.
                new_total = total_raw_pnl
                try:
                    o2, c2 = runlilopxy.process_lilo_orders(client)
                    if not _both_empty(o2, c2):
                        new_total = compute_totals(o2, c2)["total"]
                except Exception as e:
                    print(f"{Fore.YELLOW}⚠️ Post-flat ledger refresh failed ({e}); using pre-flat total.")

                print(f"🧹 {Fore.GREEN}Broker flat verified! Locking offset at ₹{new_total:,.0f} and restarting engine...")
                pnl_offset = new_total
                winners_peak_brick = 0.0
                consecutive_breaches = 0
                active_trailing_exit = INITIAL_LOSS_FLOOR
                current_game_pnl = 0.0
                save_check_state(0)
            else:
                print(f"{Fore.RED}⚠️ Broker not flat after {FLAT_CONFIRM_TIMEOUT_SECONDS:.0f}s. "
                      f"Keeping breach count; square-off retries next tick.")
    else:
        if consecutive_breaches > 0:
            consecutive_breaches = 0
            save_check_state(0)

    # 8. Final sync (always carries today's timestamp)
    save_session_state(winners_peak_brick, current_game_pnl, active_trailing_exit, pnl_offset)


if __name__ == "__main__":
    pipe_master_execution_ledger()
