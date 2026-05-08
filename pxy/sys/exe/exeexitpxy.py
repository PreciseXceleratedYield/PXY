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
DEBUG_MODE = True 

def debug_log(msg, color=Fore.BLUE):
    if DEBUG_MODE:
        # Removed \n from debug logs to prevent extra spacing
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
        
        if ltp <= 0 or entry <= 0:
            return "%00⚪ 00%", False

        entry_pct = int(((ltp - entry) / entry) * 100)
        tgt_pct = int(((tgt - ltp) / entry) * 100)
        
        entry_pct = max(-99, min(99, entry_pct))
        tgt_pct = max(0, min(99, tgt_pct))

        color, dot = (Fore.GREEN, "🟢") if entry_pct > 0 else (Fore.RED, "🔴") if entry_pct < 0 else (Fore.WHITE, "⚪")
        st_str = f"{color}%{abs(entry_pct):02d}{dot}{Fore.RESET} {tgt_pct:02d}%"
        return st_str, (ltp >= tgt)
    except:
        return "%00⚪ 00%", False

def run_snapshot():
    debug_log("Starting run_snapshot loop...")
    IST = pytz.timezone("Asia/Kolkata")
    now = datetime.now(IST).time()

    if dt_time(15, 19) <= now < dt_time(15, 30):
        try:
            exe_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "exesqrpxy.py")
            if os.path.exists(exe_path):
                subprocess.run(["python3", exe_path], check=True)
        except Exception as e:
            print(f"{Fore.RED}❌ Square-off Error: {e}")

    # Fetch Data
    data = get_combined_data()
    df = data.get("active_orders", pd.DataFrame())
    client = get_session()

    if df.empty:
        print(f"{Fore.YELLOW}No active orders. System idling...")
        return

    # Handle Averaging
    handle_side_averaging(client, df)

    # Render Dashboard
    print("━" * 42)
    print(f" {Fore.CYAN}{Style.BRIGHT}{'SYMBOL':<21}{'ST':^10}{'PNL':>8}")
    print("-" * 42)

    for idx, r in df.iterrows():
        # Keep original symbol name for clarity as requested
        sym = str(r.get('symbol',''))[:21] 
        st_display, is_target_hit = compute_st_fixed(r)
        
        if is_target_hit:
            place_exit_order(client, r)
        
        pnl_val = int(r.get('pnl', 0))
        p_col = Fore.GREEN if pnl_val > 0 else Fore.RED if pnl_val < 0 else Fore.WHITE
        # Tightened string formatting
        print(f" {sym:<21}{st_display:<12}{p_col}{pnl_val:>8}")

    print("-" * 42)
    print(f"{Fore.WHITE}Refreshed: {datetime.now(IST).strftime('%H:%M:%S')}")

if __name__ == "__main__":
    run_snapshot()

