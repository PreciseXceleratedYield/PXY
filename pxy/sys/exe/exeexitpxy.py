# # exeexitpxy.py
import pandas as pd 
import os 
import json 
import sys
import time 
import re
import subprocess 
from datetime import datetime
from pathlib import Path
from colorama import init, Fore, Style 

SYS_DIR = Path(__file__).resolve().parent.parent
if str(SYS_DIR) not in sys.path:
    sys.path.insert(0, str(SYS_DIR))

from syscnfgpxy import (
    EXEEXITPXY_DEBUG_ENABLED as DEBUG_MODE,
    EXEEXITPXY_EXIT_LOCK_KEEP_SECS,
    EXEEXITPXY_DEPTH_EXIT_THRESHOLD,
    EXEEXITPXY_ORDER_AMO,
    EXEEXITPXY_ORDER_EXCHANGE_SEGMENT,
    EXEEXITPXY_ORDER_PRICE,
    EXEEXITPXY_ORDER_PRODUCT,
    EXEEXITPXY_ORDER_TRANSACTION_TYPE,
    EXEEXITPXY_ORDER_TYPE,
    EXEEXITPXY_ORDER_VALIDITY,
    EXEEXITPXY_PNL_EXIT_MIN,
    EXEEXITPXY_SQUAREOFF_SCRIPT,
    EXEEXITPXY_SQUAREOFF_TIMEOUT_SECS,
    EXEEXITPXY_SQOFF_ALL_START,
    EXEEXITPXY_SQOFF_END,
    EXEEXITPXY_SQOFF_MIN_GAP_SECS,
    EXEEXITPXY_SQOFF_START,
    EXEEXITPXY_SYSDUMP_SCRIPT,
    SYSCNFGPXY_ACTION_COOLDOWN_SECONDS,
    SYSCNFGPXY_TIMEZONE,
)
from sysmodepxy import dispatch_mode
from sysdecisionpxy import (
    counter_leg_allowed,
    exit_order_response_accepted,
    exit_lock_recent,
    exit_quantity_to_sell,
    matching_exit_net_quantity,
    target_exit_allowed,
    valid_exit_positions_response,
)

from exeomspxy import get_combined_data 
from runclntpxy import get_session 
from runexlckpxy import ledger_busy      # stand the counter-buy down while the ledger lock is held
from runlilopxy import position_net_quantity

# IMPORT SYSTEM CO-PROCESSOR 
from exeexppxy import analyze_targets_and_sides, process_metrics_print_and_dump, dump_idle_json

# COUNTER-BUY (CBUY) TRIGGER
try:
    from execbuypxy import check_counter_leg
except ImportError as _buy_err:
    print(f"{Fore.YELLOW}⚠️ execbuypxy not loaded ({_buy_err}); counter-leg check disabled.")
    check_counter_leg = lambda remaining_df: None

init(autoreset=True) 

# ==================== CONFIG (this file's settings) ====================
PNL_EXIT_MIN = EXEEXITPXY_PNL_EXIT_MIN
EXIT_LOCK_SECS = SYSCNFGPXY_ACTION_COOLDOWN_SECONDS
EXIT_LOCK_FILE_NAME = ".exit_lock.json"
EXIT_LOCK_KEEP_SECS = EXEEXITPXY_EXIT_LOCK_KEEP_SECS

# Square-off windows; all new buys stop at 15:10 before square-off begins.
SQUAREOFF_SCRIPT = EXEEXITPXY_SQUAREOFF_SCRIPT
SQOFF_START = EXEEXITPXY_SQOFF_START
SQOFF_ALL_START = EXEEXITPXY_SQOFF_ALL_START
SQOFF_END = EXEEXITPXY_SQOFF_END
SQUAREOFF_TIMEOUT_SECS = EXEEXITPXY_SQUAREOFF_TIMEOUT_SECS
SQOFF_MIN_GAP_SECS = EXEEXITPXY_SQOFF_MIN_GAP_SECS
SYSDUMP_SCRIPT = EXEEXITPXY_SYSDUMP_SCRIPT

# Exit order parameters (this pipe only submits sell orders)
ORDER_EXCHANGE_SEGMENT = EXEEXITPXY_ORDER_EXCHANGE_SEGMENT
ORDER_PRODUCT = EXEEXITPXY_ORDER_PRODUCT
ORDER_PRICE = EXEEXITPXY_ORDER_PRICE
ORDER_TYPE = EXEEXITPXY_ORDER_TYPE
ORDER_VALIDITY = EXEEXITPXY_ORDER_VALIDITY
ORDER_TRANSACTION_TYPE = EXEEXITPXY_ORDER_TRANSACTION_TYPE
ORDER_AMO = EXEEXITPXY_ORDER_AMO
# =======================================================================

_LOCK_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), EXIT_LOCK_FILE_NAME)

def _lock_key(row):
    # symbol + tag + buy_time identifies one lot; stable across cycles, distinct between lots
    return f"{row.get('symbol', '')}|{row.get('tag', '')}|{row.get('buy_time', '')}"

def _load_locks():
    """Reads the lock file; returns {} if missing/unreadable. Never raises."""
    try:
        if os.path.exists(_LOCK_FILE):
            with open(_LOCK_FILE, "r") as fh:
                return json.load(fh)
    except Exception:
        pass
    return {}

def _recent(data, key, secs):
    """True if `key` was recorded within `secs` seconds. Never raises."""
    return exit_lock_recent(data, key, secs, time.time())

def _mark_lock(key):
    """Records `key` with the current time; prunes stale entries. Never raises."""
    try:
        data = _load_locks()
        now = time.time()
        data = {k: v for k, v in data.items() if now - float(v) < EXIT_LOCK_KEEP_SECS}
        data[key] = now
        tmp = _LOCK_FILE + ".tmp"
        with open(tmp, "w") as fh:
            json.dump(data, fh)
        os.replace(tmp, _LOCK_FILE)
    except Exception:
        pass

def _recently_exited(key):
    """True if a sell for this lot was sent within EXIT_LOCK_SECS."""
    return _recent(_load_locks(), key, EXIT_LOCK_SECS)

def _mark_exited(key):
    """Records a sent sell (skipped when EXIT_LOCK_SECS is 0)."""
    if EXIT_LOCK_SECS <= 0:
        return
    _mark_lock(key)


def depth_squareoff_side(entry_signal, past_depth, threshold=EXEEXITPXY_DEPTH_EXIT_THRESHOLD):
    """Return the opposing option side to square off for a deep reversal."""
    signal = str(entry_signal).upper().strip()
    parsed_depth = re.fullmatch(r"(CE|PE)(\d+)", str(past_depth).upper().strip())
    if not parsed_depth:
        return None

    depth_side, depth_value = parsed_depth.groups()
    if int(depth_value) <= threshold:
        return None
    if signal == "BUY" and depth_side == "PE":
        return "PE"
    if signal == "SELL" and depth_side == "CE":
        return "CE"
    return None


def run_depth_squareoff(client, active_df, market_data_available,
                        positions_unverified=False):
    """Close only the losing-direction side after a confirmed deep reversal."""
    if active_df is None or active_df.empty or not market_data_available:
        return set()
    if positions_unverified or ledger_busy():
        print(f"{Fore.YELLOW}⚠️ Depth-based square-off skipped: positions unavailable or ledger busy.")
        return set()

    snapshot = active_df.iloc[0]
    side = depth_squareoff_side(
        snapshot.get("entry"),
        snapshot.get("hkin_past_depth"),
    )
    if side is None:
        return set()

    signal_time = str(snapshot.get("hkin_signal_time", "")).strip()
    if not signal_time or signal_time.lower() in {"none", "nan"}:
        print(f"{Fore.YELLOW}⚠️ Depth-based square-off skipped: signal candle time unavailable.")
        return set()

    signal_key = f"DEPTH_EXIT|{side}|{signal_time}"
    if _recent(_load_locks(), signal_key, EXIT_LOCK_KEEP_SECS):
        debug_log(f"Depth exit {signal_key} already sent; skipping duplicate.")
        return set()

    print(
        f"{Fore.YELLOW}⚠️ Deep reversal: {snapshot.get('entry')} with "
        f"{snapshot.get('hkin_past_depth')} past depth; squaring off {side}."
    )
    exited_keys = set()
    order_accepted = False
    for _, row in active_df.iterrows():
        symbol = str(row.get("symbol", "")).upper()
        if not symbol.endswith(side):
            continue
        key = _lock_key(row)
        if _recently_exited(key):
            continue
        if verify_and_exit(client, row):
            exited_keys.add(key)
            order_accepted = True

    if order_accepted:
        _mark_lock(signal_key)
    return exited_keys


def debug_log(msg, color=Fore.BLUE): 
    if DEBUG_MODE: 
        print(f"{color}[DEBUG] {msg}{Style.RESET_ALL}") 

def get_sell_suffix():
    """Generates an explicit sell suffix code with millisecond resolution"""
    ms = datetime.now(SYSCNFGPXY_TIMEZONE).strftime('%f')[:-3]
    return f"_S{ms}" 

def _order_accepted(response):
    """Accept only the successful response shape documented by the Kotak Neo SDK."""
    return exit_order_response_accepted(response)

def place_exit_order(client, row): 
    """Triggers Sell order by appending an explicit _S{ms} suffix to the entry tag.""" 
    try: 
        existing_tag = row.get('tag') 
        
        if existing_tag and str(existing_tag).lower() not in ['nan', 'none', '']: 
            base_tag = str(existing_tag).split('_')[0].strip()
        else: 
            base_tag = datetime.now(SYSCNFGPXY_TIMEZONE).strftime('%H%M%S')
            
        final_tag = f"{base_tag}{get_sell_suffix()}"
            
        params = { 
            "exchange_segment": ORDER_EXCHANGE_SEGMENT, 
            "product": ORDER_PRODUCT, 
            "price": ORDER_PRICE, 
            "order_type": ORDER_TYPE, 
            "quantity": str(abs(int(row.get('qty', 0)))), 
            "validity": ORDER_VALIDITY, 
            "trading_symbol": str(row.get('symbol', '')), 
            "transaction_type": ORDER_TRANSACTION_TYPE,
            "amo": ORDER_AMO, 
            "tag": final_tag 
        } 
        
        debug_log(f"Attempting API exit payload: {params}", Fore.YELLOW) 
        order_response = client.place_order(**params) 
        debug_log(f"Broker Raw API Response: {order_response}", Fore.GREEN) 
        
        if not _order_accepted(order_response):
            print(f"{Fore.RED}❌ Broker did not confirm exit order acceptance: {order_response!r}")
            return None

        print(f"{Fore.MAGENTA}{Style.BRIGHT}⚡ ORDER ACCEPTED BY BROKER: {params['trading_symbol']} | TAG: {final_tag}")
        try:
            parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            script_path = os.path.join(parent_dir, SYSDUMP_SCRIPT)
            if os.path.exists(script_path):
                subprocess.Popen([sys.executable or "python3", script_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                print(f"{Fore.RED}❌ Script not found at {script_path}")
        except Exception as script_err:
            print(f"{Fore.RED}❌ Error launching script: {script_err}")
        return order_response 
        
    except Exception as e: 
        print(f"{Fore.RED}❌ Exit Order Error: {e}") 
        return None 

def verify_and_exit(client, row): 
    return dispatch_mode("verify_and_exit", lambda client, row: _verify_and_exit_production(client, row), client, row)


def _verify_and_exit_production(client, row):
    try:
        symbol = str(row.get('symbol', '')) 
        pos_res = client.positions() 
        if not valid_exit_positions_response(pos_res):
            print(f"{Fore.RED}⚠️ Safety Block: Could not verify positions.") 
            return 
            
        key = _lock_key(row)
        if _recently_exited(key):
            print(f"{Fore.YELLOW}🚫 Blocked: exit already sent for [{symbol}] within {EXIT_LOCK_SECS}s.")
            return

        net_qty = matching_exit_net_quantity(
            pos_res["data"], symbol, position_net_quantity
        )
        if net_qty is not None:
            if net_qty > 0: 
                row = row.copy()
                row['qty'] = exit_quantity_to_sell(net_qty, row.get('qty', 0))
                if row["qty"] <= 0:
                    print(f"{Fore.YELLOW}🚫 Blocked: requested exit quantity is not positive.")
                    return
                resp = place_exit_order(client, row)
                if resp:
                    _mark_exited(key)
                return resp
            else: 
                print(f"{Fore.YELLOW}🚫 Blocked: Net Qty calculated: {net_qty}") 
        else: 
            print(f"{Fore.YELLOW}🚫 Blocked: [{symbol}] not found in broker positions.") 
    except Exception as e: 
        print(f"{Fore.RED}❌ Safety Check Crash: {e}")

def run_snapshot():
    if not dispatch_mode("engine_window_open", lambda: True):
        print(f"{Fore.YELLOW}CHK engine paused during market hours; exit pipe not run.")
        return

    now = datetime.now(SYSCNFGPXY_TIMEZONE).time()
    
    # Base path to the script
    exe_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), SQUAREOFF_SCRIPT)
    
    if dispatch_mode("allow_squareoff", lambda: True) and os.path.exists(exe_path):
        sq_args, sq_key = None, None
        if SQOFF_START <= now < SQOFF_ALL_START:       # 15:11 up to 15:14: without -all
            sq_args, sq_key = [], "SQOFF|first"
        elif SQOFF_ALL_START <= now < SQOFF_END:       # 15:14 up to 15:50: with -all
            sq_args, sq_key = ["-all"], "SQOFF|all"
        if sq_args is not None:
            if ledger_busy():
                print(f"{Fore.YELLOW}⚠️ Ledger lock held (liquidation may be running); square-off skipped this cycle.")
            elif _recent(_load_locks(), sq_key, SQOFF_MIN_GAP_SECS):
                debug_log(f"Square-off {sq_key} already launched within {SQOFF_MIN_GAP_SECS}s; skipping.")
            else:
                _mark_lock(sq_key)          # before the run, so a hang or crash cannot cause a relaunch loop
                try:
                    subprocess.run([sys.executable or "python3", exe_path] + sq_args,
                                   check=True, timeout=SQUAREOFF_TIMEOUT_SECS)
                except subprocess.TimeoutExpired:
                    print(f"{Fore.RED}❌ Square-off timed out after {SQUAREOFF_TIMEOUT_SECS}s.")
                except Exception as e:
                    print(f"{Fore.RED}❌ Square-off Error: {e}")

    data = get_combined_data() 
    df = data.get("active_orders", pd.DataFrame()) 
    client = get_session() 
    if data.get("error"):
        print(f"{Fore.RED}⚠️ Data error this cycle (see OMS DATA ERROR above). Skipping; dashboard left untouched.")
        return
    if df.empty: 
        print(f"{Fore.YELLOW}No active orders. System idling...") 
        dump_idle_json("one")
        return 

    depth_exited_keys = set()
    if not SQOFF_START <= now < SQOFF_END:
        depth_exited_keys = run_depth_squareoff(
            client,
            df,
            data.get("market_snapshot_available"),
            data.get("positions_unverified", False),
        )
        
    # Display-only analysis: a failure here must never block the exit loop below
    try:
        side_all_targets_hit = analyze_targets_and_sides(df)
    except Exception as e:
        print(f"{Fore.RED}⚠️ Target analysis error (display only): {e}")
        side_all_targets_hit = {"CE": False, "PE": False}

    # Proactive Core Execution Routing Logic Block (Pure Single Targets)
    exited_keys = set(depth_exited_keys)
    if not data.get("market_snapshot_available"):
        print(f"{Fore.YELLOW}⚠️ Market snapshot unavailable; target exits skipped this cycle.")
    else:
        for idx, r in df.iterrows():
            # One bad row must not stop the remaining rows from being evaluated
            try:
                if _lock_key(r) in exited_keys:
                    continue
                sym = str(r.get('symbol', ''))
                ltp = float(r.get("sell_prc", 0))
                tgt = float(r.get("pxy_tgt", 0))
                pnl = float(r.get("pnl", 0))

                debug_log(f"Global Enforced Single Exit Mode ({sym}). Mode: SINGLE TARGET.", Fore.GREEN)

                # Pure Linear Target Evaluation Pool
                if target_exit_allowed(
                    data.get("market_snapshot_available"),
                    tgt,
                    ltp,
                    pnl,
                    PNL_EXIT_MIN,
                ):
                    print(f"{Fore.GREEN}🎯 Target Hit & PnL Met ({sym}): LTP {ltp} >= TGT {tgt} | PnL {pnl} >= {PNL_EXIT_MIN} [Execution Mode: ONE]")
                    if verify_and_exit(client, r):
                        exited_keys.add(_lock_key(r))
            except Exception as e:
                print(f"{Fore.RED}❌ Row evaluation error ({r.get('symbol', '?')}): {e}")

    # Counter-leg check on whatever is still held after the target exits
    # (rows exited this cycle, or with an exit still in flight, are not counted as held)
    try:
        locks = _load_locks()
        held_mask = []
        for _, r in df.iterrows():
            k = _lock_key(r)
            held_mask.append(k not in exited_keys and not _recent(locks, k, EXIT_LOCK_SECS))
        is_ledger_busy = ledger_busy()
        if not data.get("market_snapshot_available"):
            print(f"{Fore.YELLOW}⚠️ Market snapshot unavailable; counter-buy skipped this cycle.")
        elif data.get("positions_unverified"):
            print(f"{Fore.YELLOW}⚠️ Broker positions not verified this cycle; counter-buy skipped.")
        elif is_ledger_busy:
            print(f"{Fore.YELLOW}⚠️ Ledger lock held (tick or liquidation running); counter-buy skipped.")
        elif counter_leg_allowed(
            data.get("market_snapshot_available"),
            data.get("positions_unverified"),
            is_ledger_busy,
        ):
            dispatch_mode(
                "run_counter_leg",
                lambda remaining_df: check_counter_leg(remaining_df),
                df[held_mask],
            )
    except Exception as e:
        print(f"{Fore.RED}❌ Counter-leg hook error: {e}")

    # Display/dump only: runs after exits, so a failure here must not crash the cycle
    try:
        process_metrics_print_and_dump(df, side_all_targets_hit, "one")
    except Exception as e:
        print(f"{Fore.RED}⚠️ Metrics/dashboard error: {e}")

if __name__ == "__main__": 
    run_snapshot()
