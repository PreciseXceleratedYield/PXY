import pandas as pd
import os
import time
import pytz
import subprocess
import re
from datetime import datetime, time as dt_time
from colorama import init, Fore, Style

from exeomspxy import get_combined_data
from runclntpxy import get_session
from exeavgpxy import handle_side_averaging

init(autoreset=True)

def place_exit_order(client, row):
    try:
        params = {
            "exchange_segment": "nse_fo", "product": "NRML", "price": "0",
            "order_type": "MKT", "quantity": str(abs(int(row.get('qty', 0)))),
            "validity": "DAY", "trading_symbol": str(row.get('symbol', '')),
            "transaction_type": "S", "amo": "NO"
        }
        print(f"{Fore.MAGENTA}{Style.BRIGHT}⚡ TGT HIT! EXITING: {params['trading_symbol']}")
        return client.place_order(**params)
    except Exception as e:
        print(f"{Fore.RED}❌ Order Error: {e}")
        return None

def compute_st_fixed(row):
    try:
        ltp = float(row.get("sell_prc", 0))
        tgt = float(row.get("pxy_tgt", 0))
        entry = float(row.get("pxy_entry", 0))
        if ltp <= 0 or entry <= 0: return "%00⚪ 00%", False

        entry_pct = max(-99, min(99, int(((ltp - entry) / entry) * 100)))
        tgt_pct = max(0, min(99, int(((tgt - ltp) / entry) * 100)))

        color, dot = (Fore.GREEN, "🟢") if entry_pct > 0 else (Fore.RED, "🔴") if entry_pct < 0 else (Fore.WHITE, "⚪")
        return f"{color}%{abs(entry_pct):02d}{dot}{Fore.RESET} {tgt_pct:02d}%", (ltp >= tgt)
    except:
        return "%00⚪ 00%", False

def run_snapshot():
    # 1. IST Time Check for Auto Exit
    IST = pytz.timezone("Asia/Kolkata")
    now = datetime.now(IST).time()
    if dt_time(15, 19) <= now < dt_time(15, 30):
        print(f"{Fore.YELLOW}⚡ Exit Window Active! Triggering ⚡")
        try:
            exe_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "exesqrpxy.py")
            subprocess.run(["python3", exe_path], check=True)
        except Exception as e:
            print(f"{Fore.RED}❌ Square-off Error: {e}")

    # 2. Fetch Data & Client
    data = get_combined_data()
    df = data.get("active_orders", pd.DataFrame())
    client = get_session()

    if df.empty:
        print(f"{Fore.YELLOW} No active orders. System idling...{Fore.RESET}")
        return

    # 3. TRIGGER AVERAGING LOGIC
    handle_side_averaging(client, df)

    # 4. DASHBOARD PRINTING
    print("━" * 42)
    print(f" {Fore.CYAN}{Style.BRIGHT}{'SYM':<19}{'ST':^12}{'PNL':>7}")
    print("-" * 42)

    for _, r in df.iterrows():
        raw_sym = str(r.get('symbol',''))
        sym = re.sub(r'^[A-Z]+\d*', '', raw_sym)[:15]
        st_display, is_target_hit = compute_st_fixed(r)
        
        if is_target_hit:
            place_exit_order(client, r)
            
        p_col = Fore.GREEN if r.get('pnl',0) > 0 else Fore.RED if r.get('pnl',0) < 0 else Fore.WHITE
        print(f" {sym:<21}{st_display:<12}{p_col}{int(r.get('pnl', 0)):>10}")

    print("-" * 42)
    print(f" {Fore.WHITE}Refreshed: {time.strftime('%H:%M:%S')}")

if __name__ == "__main__":
    run_snapshot()

