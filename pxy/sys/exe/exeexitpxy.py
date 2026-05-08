import pandas as pd
import os
import time
import pytz
import subprocess
import re
from datetime import datetime, time as dt_time
from colorama import init, Fore, Style

# External Dependency Imports
from exeomspxy import get_combined_data
from runclntpxy import get_session
from exeavgpxy import handle_side_averaging

init(autoreset=True)

# --- DEBUG CONFIG ---
DEBUG_MODE = True  # Set to False to hide detailed logs

def debug_log(msg, color=Fore.BLUE):
    if DEBUG_MODE:
        print(f"{color}[DEBUG] {msg}{Style.RESET_ALL}")

def place_exit_order(client, row):
    try:
        params = {
            "exchange_segment": "nse_fo",
            "product": "NRML",
            "price": "0",
            "order_type": "MKT",
            "quantity": str(abs(int(row.get('qty', 0)))),
            "validity": "DAY",
            "trading_symbol": str(row.get('symbol', '')),
            "transaction_type": "S",
            "amo": "NO"
        }
        print(f"{Fore.MAGENTA}{Style.BRIGHT}⚡ TGT HIT! EXITING: {params['trading_symbol']}")
        return client.place_order(**params)
    except Exception as e:
        print(f"{Fore.RED}❌ Exit Order Error: {e}")
        return None

def compute_st_fixed(row):
    """Calculates status string and target hit boolean."""
    try:
        ltp = float(row.get("sell_prc", 0))
        tgt = float(row.get("pxy_tgt", 0))
        entry = float(row.get("pxy_entry", 0))
        
        debug_log(f"Calc for {row.get('symbol')}: LTP={ltp}, TGT={tgt}, EN={entry}", Fore.BLACK + Style.DIM)

        if ltp <= 0 or entry <= 0:
            return "%00⚪ 00%", False

        entry_pct = int(((ltp - entry) / entry) * 100)
        tgt_pct = int(((tgt - ltp) / entry) * 100)
        
        entry_pct = max(-99, min(99, entry_pct))
        tgt_pct = max(0, min(99, tgt_pct))

        color, dot = (Fore.GREEN, "🟢") if entry_pct > 0 else (Fore.RED, "🔴") if entry_pct < 0 else (Fore.WHITE, "⚪")
        st_str = f"{color}%{abs(entry_pct):02d}{dot}{Fore.RESET} {tgt_pct:02d}%"
        
        return st_str, (ltp >= tgt)
    except Exception as e:
        debug_log(f"Compute Error: {e}", Fore.RED)
        return "%00⚪ 00%", False

def run_snapshot():
    debug_log("Starting run_snapshot loop...")
    
    # 1. Square-off Window Check
    IST = pytz.timezone("Asia/Kolkata")
    now = datetime.now(IST).time()
    debug_log(f"Current IST Time: {now.strftime('%H:%M:%S')}")

    if dt_time(15, 19) <= now < dt_time(15, 30):
        debug_log("Inside Square-off Window (15:19 - 15:30)", Fore.YELLOW)
        try:
            exe_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "exesqrpxy.py")
            debug_log(f"Checking for square-off script at: {exe_path}")
            if os.path.exists(exe_path):
                subprocess.run(["python3", exe_path], check=True)
            else:
                print(f"{Fore.RED}File not found: exesqrpxy.py")
        except Exception as e:
            print(f"{Fore.RED}❌ Square-off Execution Error: {e}")

    # 2. Fetch Data
    debug_log("Fetching combined data from exeomspxy...")
    data = get_combined_data()
    df = data.get("active_orders", pd.DataFrame())
    
    debug_log("Authenticating with runclntpxy...")
    client = get_session()

    if df.empty:
        debug_log("Dataframe is EMPTY. No active trades found.", Fore.YELLOW)
        print(f"{Fore.YELLOW} No active orders. System idling...{Fore.RESET}")
        return

    debug_log(f"Found {len(df)} active orders.")

    # 3. Handle Averaging
    debug_log("Calling handle_side_averaging (exeavgpxy)...")
    handle_side_averaging(client, df)

    # 4. Render Dashboard
    print("━" * 42)
    print(f" {Fore.CYAN}{Style.BRIGHT}{'SYM':<19}{'ST':^12}{'PNL':>7}")
    print("-" * 42)

    for idx, r in df.iterrows():
        raw_sym = str(r.get('symbol',''))
        sym = re.sub(r'^[A-Z]+\d*', '', raw_sym)[:15]
        
        st_display, is_target_hit = compute_st_fixed(r)
        
        if is_target_hit:
            debug_log(f"TARGET REACHED for {raw_sym}! Triggering exit...", Fore.MAGENTA)
            place_exit_order(client, r)
        
        pnl_val = int(r.get('pnl', 0))
        p_col = Fore.GREEN if pnl_val > 0 else Fore.RED if pnl_val < 0 else Fore.WHITE
        print(f" {sym:<21}{st_display:<12}{p_col}{pnl_val:>10}")

    print("-" * 42)
    print(f" {Fore.WHITE}Refreshed: {time.strftime('%H:%M:%S')}")
    debug_log("Snapshot cycle complete.\n")

if __name__ == "__main__":
    run_snapshot()
