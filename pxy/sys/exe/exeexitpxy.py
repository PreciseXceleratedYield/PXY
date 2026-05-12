# exit_script.py
import pandas as pd
import os
import time
import pytz
import subprocess
from datetime import datetime, time as dt_time
from colorama import init, Fore, Style

# External Dependency Imports
from exeomspxy import get_combined_data
from runclntpxy import get_session
from exeavgpxy import handle_side_averaging

init(autoreset=True)

# --- DEBUG CONFIG ---
DEBUG_MODE = False

def debug_log(msg, color=Fore.BLUE):
    if DEBUG_MODE:
        print(f"{color}[DEBUG] {msg}{Style.RESET_ALL}")

def generate_pxy_tag():
    """Generates a pure timestamp tag: HHMMSS"""
    IST = pytz.timezone("Asia/Kolkata")
    return datetime.now(IST).strftime('%H%M%S')

def place_exit_order(client, row):
    """Internal function to trigger the Sell order with the matching Tag."""
    try:
        # Retrieve the tag from the cleaned OMS 'tag' column
        existing_tag = row.get('tag')
        
        # Use existing tag (UUID or Timestamp) to ensure LILO matching
        if existing_tag and str(existing_tag).lower() not in ['nan', 'none', '']:
            final_tag = str(existing_tag).strip()
        else:
            final_tag = generate_pxy_tag()

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
            "tag": final_tag 
        }
        print(f"{Fore.MAGENTA}{Style.BRIGHT}⚡ TGT HIT! EXITING: {params['trading_symbol']} | TAG: {final_tag}")
        return client.place_order(**params)
    except Exception as e:
        print(f"{Fore.RED}❌ Exit Order Error: {e}")
        return None

def verify_and_exit(client, row):
    """SAFETY CHECK: Verifies with Broker (Kotak Neo) before selling."""
    try:
        # 1. Fetch real-time positions from Broker
        pos_res = client.positions()
        if not pos_res or "data" not in pos_res:
            print(f"{Fore.RED}⚠️ Safety Block: Could not verify positions with broker.")
            return

        pos_df = pd.DataFrame(pos_res["data"])
        symbol = str(row.get('symbol', ''))
        
        # 2. Check if symbol exists and has a positive net quantity
        # flBuyQty - flSellQty = Net Holdings
        match = pos_df[pos_df['trdSym'] == symbol]
        
        if not match.empty:
            # Sum up net qty just in case there are multiple entries
            net_qty = int(match['flBuyQty'].sum()) - int(match['flSellQty'].sum())
            
            if net_qty > 0:
                # 3. Everything is safe -> Place the exit order
                return place_exit_order(client, row)
            else:
                print(f"{Fore.YELLOW}🚫 Blocked: No active long position for {symbol} (Net Qty: {net_qty})")
        else:
            print(f"{Fore.YELLOW}🚫 Blocked: Symbol {symbol} not found in broker positions.")
            
    except Exception as e:
        print(f"{Fore.RED}❌ Safety Check Error: {e}")

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
    IST = pytz.timezone("Asia/Kolkata")
    now = datetime.now(IST).time()

    # Square-off logic at 3:23 PM
    if dt_time(15, 23) <= now < dt_time(15, 30):
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
        sym = str(r.get('symbol',''))[:21]
        st_display, is_target_hit = compute_st_fixed(r)
        
        # Trigger Exit with Safety Verification
        if is_target_hit:
            verify_and_exit(client, r)

        pnl_val = int(r.get('pnl', 0))
        p_col = Fore.GREEN if pnl_val > 0 else Fore.RED if pnl_val < 0 else Fore.WHITE
        print(f" {sym:<21}{st_display:<12}{p_col}{pnl_val:>8}")

    print("-" * 42)
    print(f"{Fore.WHITE}Refreshed: {datetime.now(IST).strftime('%H:%M:%S')}")

if __name__ == "__main__":
    run_snapshot()

