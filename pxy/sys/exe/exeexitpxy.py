import pandas as pd
import os
import time
from colorama import init, Fore, Style
from exeomspxy import get_combined_data
import pytz
import subprocess  # <-- for triggering exesqrpxy.py
from datetime import datetime, time as dt_time
import re 
init(autoreset=True)

def place_exit_order(client, row):
    """Executes Market Sell to exit the position once Target is hit."""
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
            "amo": "NO",
            "disclosed_quantity": "0",
            "market_protection": "0"
        }
        
        print(f"{Fore.MAGENTA}{Style.BRIGHT}⚡ TGT HIT! EXITING: {params['trading_symbol']}")
        res = client.place_order(**params)
        return res
    except Exception as e:
        print(f"{Fore.RED}❌ Order Error: {e}")
        return None

def compute_st_fixed(row):
    try:
        ltp = float(row.get("sell_prc", 0))
        tgt = float(row.get("pxy_tgt", 0))
        entry = float(row.get("pxy_entry", 0))

        if ltp <= 0 or entry <= 0:
            return "%00⚪ 00%", False

        # --- % calculations ---
        entry_pct = int(((ltp - entry) / entry) * 100)
        tgt_pct   = int(((tgt - ltp) / entry) * 100)

        # --- clamp ---
        entry_pct = max(-99, min(99, entry_pct))
        tgt_pct   = max(0, min(99, tgt_pct))

        # --- LEFT SIDE COLOR ONLY ---
        if entry_pct > 0:
            color = Fore.GREEN
            dot = "🟢"
        elif entry_pct < 0:
            color = Fore.RED
            dot = "🔴"
        else:
            color = Fore.WHITE
            dot = "⚪"

        entry_s = f"{abs(entry_pct):02d}"
        tgt_s   = f"{tgt_pct:02d}"

        # --- target hit ---
        is_hit = ltp >= tgt

        # --- FINAL FORMAT ---
        # LEFT = colored, RIGHT = plain white (no color carry)
        return f"{color}%{entry_s}{dot}{Fore.RESET} {tgt_s}%", is_hit

    except:
        return "%00⚪ 00%", False

def run_snapshot():
    # --- IST Time Check for Auto Exit ---
    IST = pytz.timezone("Asia/Kolkata")
    now = datetime.now(IST).time()
    exit_start = dt_time(15, 19)  # 3:19 PM
    exit_end   = dt_time(15, 30)  # 3:30 PM
    
    if exit_start <= now < exit_end:
        print(f"{Fore.YELLOW}⚡ Exit Window Active! Triggering ⚡")
        try:
            # Dynamically get the path of exesqrpxy.py in the same folder as this script
            SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
            exe_path = os.path.join(SCRIPT_DIR, "exesqrpxy.py")
            subprocess.run(["python3", exe_path], check=True)
        except Exception as e:
            print(f"{Fore.RED}❌ Failed to run exesqrpxy.py: {e}")

    # --- Original Functionality ---
    data = get_combined_data()
    df = data.get("active_orders", pd.DataFrame())
    
    from runclntpxy import get_session
    client = get_session()

    if df.empty:
        print(f"{Fore.YELLOW}    No active orders. System idling...{Fore.RESET}")
        return
    print("━" * 42)
    # 40-char GRID: SYM(15) ST(12) PNL(10) ~ total 40
    header = f"{'SYM':<19}{'ST':^12}{'PNL':>7}"
    print(f"  {Fore.CYAN}{Style.BRIGHT}{header}")
    print("-" * 42)

    for _, r in df.iterrows():
        raw_sym = str(r.get('symbol',''))

        sym = re.sub(r'^[A-Z]+\d*', '', raw_sym)[:15]
        
        st_display, is_target_hit = compute_st_fixed(r)
        if is_target_hit:
            place_exit_order(client, r)
        
        pnl = int(r.get('pnl', 0))
        p_col = Fore.GREEN if pnl > 0 else Fore.RED if pnl < 0 else Fore.WHITE
        
        # Print only symbol, ST, PNL
        print(f"  {sym:<21}{st_display:<12}{p_col}{pnl:>10}")
    
    print("-" * 42)
    print(f"  {Fore.WHITE}Refreshed: {time.strftime('%H:%M:%S')}")

if __name__ == "__main__":
    run_snapshot()

