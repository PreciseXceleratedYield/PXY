# # exeexitpxy.py
import pandas as pd 
import os 
import json 
import sys
import time 
import pytz 
import subprocess 
from datetime import datetime, time as dt_time 
from colorama import init, Fore, Style 

from exeomspxy import get_combined_data 
from runclntpxy import get_session 
from runexlckpxy import ledger_busy      # stand the counter-buy down while the ledger lock is held

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
DEBUG_MODE = True             # prints the order payload and the raw broker response (turn off after Monday)
PNL_EXIT_MIN = 140            # absolute PnL required alongside the target hit
EXIT_LOCK_SECS = 5            # block a repeat sell for the same lot (symbol+tag+buy_time) for this long (0 = off)
EXIT_LOCK_FILE_NAME = ".exit_lock.json"
EXIT_LOCK_KEEP_SECS = 600     # lock entries older than this are pruned from the lock file

# Square-off windows (keep CBUY_CUTOFF in execbuypxy.py equal to SQOFF_START)
SQUAREOFF_SCRIPT = "exesqrpxy.py"
SQOFF_START = dt_time(15, 14)      # from here: run square-off script (without -all)
SQOFF_ALL_START = dt_time(15, 15)  # from here: run square-off script with -all
SQOFF_END = dt_time(15, 50)        # from here: no square-off call
SQUAREOFF_TIMEOUT_SECS = 120   # a hung square-off script must not freeze the pipe
SQOFF_MIN_GAP_SECS = 20        # do not relaunch the same square-off call more often than this
SYSDUMP_SCRIPT = "sysddmppxy.py"   # launched (one folder up) after an exit order is placed

# Exit order parameters (transaction_type "S" stays in the code: this file only ever sells)
ORDER_EXCHANGE_SEGMENT = "nse_fo"
ORDER_PRODUCT = "NRML"
ORDER_PRICE = "0"
ORDER_TYPE = "MKT"
ORDER_VALIDITY = "DAY"
ORDER_AMO = "NO"
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
    if secs <= 0:
        return False
    try:
        return (time.time() - float(data.get(key, 0))) < secs
    except Exception:
        return False

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

def debug_log(msg, color=Fore.BLUE): 
    if DEBUG_MODE: 
        print(f"{color}[DEBUG] {msg}{Style.RESET_ALL}") 

def get_sell_suffix():
    """Generates an explicit sell suffix code with millisecond resolution"""
    IST = pytz.timezone("Asia/Kolkata")
    ms = datetime.now(IST).strftime('%f')[:-3]
    return f"_S{ms}" 

def place_exit_order(client, row): 
    """Triggers Sell order by appending an explicit _S{ms} suffix to the entry tag.""" 
    try: 
        existing_tag = row.get('tag') 
        
        if existing_tag and str(existing_tag).lower() not in ['nan', 'none', '']: 
            base_tag = str(existing_tag).split('_')[0].strip()
        else: 
            IST = pytz.timezone("Asia/Kolkata")
            base_tag = datetime.now(IST).strftime('%H%M%S')
            
        final_tag = f"{base_tag}{get_sell_suffix()}"
            
        params = { 
            "exchange_segment": ORDER_EXCHANGE_SEGMENT, 
            "product": ORDER_PRODUCT, 
            "price": ORDER_PRICE, 
            "order_type": ORDER_TYPE, 
            "quantity": str(abs(int(row.get('qty', 0)))), 
            "validity": ORDER_VALIDITY, 
            "trading_symbol": str(row.get('symbol', '')), 
            "transaction_type": "S", 
            "amo": ORDER_AMO, 
            "tag": final_tag 
        } 
        
        debug_log(f"Attempting API exit payload: {params}", Fore.YELLOW) 
        order_response = client.place_order(**params) 
        debug_log(f"Broker Raw API Response: {order_response}", Fore.GREEN) 
        
        if isinstance(order_response, dict):
            stat_str = str(order_response.get('stat', '')).lower()
            err_msg = str(order_response.get('errMsg', '')).lower()
            if "failed" in stat_str or "error" in err_msg or "error" in stat_str:
                print(f"{Fore.RED}❌ BROKER CORE REJECTED ORDER: {err_msg} | {stat_str}")
                return None
        
        if order_response: 
            print(f"{Fore.MAGENTA}{Style.BRIGHT}⚡ ORDER PLACED ON EXCHANGE: {params['trading_symbol']} | TAG: {final_tag}") 
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
    try: 
        symbol = str(row.get('symbol', '')) 
        pos_res = client.positions() 
        if not pos_res or "data" not in pos_res: 
            print(f"{Fore.RED}⚠️ Safety Block: Could not verify positions.") 
            return 
            
        key = _lock_key(row)
        if _recently_exited(key):
            print(f"{Fore.YELLOW}🚫 Blocked: exit already sent for [{symbol}] within {EXIT_LOCK_SECS}s.")
            return

        pos_df = pd.DataFrame(pos_res["data"]) 
        match = pos_df[pos_df['trdSym'] == symbol].copy()
        if not match.empty: 
            for c in ("flBuyQty", "flSellQty"):
                match[c] = pd.to_numeric(match[c], errors="coerce").fillna(0)
            net_qty = int(match['flBuyQty'].sum() - match['flSellQty'].sum()) 
            if net_qty > 0: 
                row = row.copy()
                row['qty'] = min(net_qty, abs(int(float(row.get('qty', 0)))))
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
    IST = pytz.timezone("Asia/Kolkata")
    now = datetime.now(IST).time()
    
    # Base path to the script
    exe_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), SQUAREOFF_SCRIPT)
    
    if os.path.exists(exe_path):
        sq_args, sq_key = None, None
        if SQOFF_START <= now < SQOFF_ALL_START:       # 15:14 up to 15:15: without -all
            sq_args, sq_key = [], "SQOFF|first"
        elif SQOFF_ALL_START <= now < SQOFF_END:       # 15:15 up to 15:50: with -all
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
        
    # Display-only analysis: a failure here must never block the exit loop below
    try:
        side_all_targets_hit = analyze_targets_and_sides(df)
    except Exception as e:
        print(f"{Fore.RED}⚠️ Target analysis error (display only): {e}")
        side_all_targets_hit = {"CE": False, "PE": False}

    # Proactive Core Execution Routing Logic Block (Pure Single Targets)
    exited_keys = set()
    for idx, r in df.iterrows():
        # One bad row must not stop the remaining rows from being evaluated
        try:
            sym = str(r.get('symbol', ''))
            ltp = float(r.get("sell_prc", 0))
            tgt = float(r.get("pxy_tgt", 0))
            pnl = float(r.get("pnl", 0))

            debug_log(f"Global Enforced Single Exit Mode ({sym}). Mode: SINGLE TARGET.", Fore.GREEN)

            # Pure Linear Target Evaluation Pool
            if tgt > 0 and ltp > 0 and ltp >= tgt and pnl >= PNL_EXIT_MIN:
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
        if data.get("positions_unverified"):
            print(f"{Fore.YELLOW}⚠️ Broker positions not verified this cycle; counter-buy skipped.")
        elif ledger_busy():
            print(f"{Fore.YELLOW}⚠️ Ledger lock held (tick or liquidation running); counter-buy skipped.")
        else:
            check_counter_leg(df[held_mask])
    except Exception as e:
        print(f"{Fore.RED}❌ Counter-leg hook error: {e}")

    # Display/dump only: runs after exits, so a failure here must not crash the cycle
    try:
        process_metrics_print_and_dump(df, side_all_targets_hit, "one")
    except Exception as e:
        print(f"{Fore.RED}⚠️ Metrics/dashboard error: {e}")

if __name__ == "__main__": 
    run_snapshot()
