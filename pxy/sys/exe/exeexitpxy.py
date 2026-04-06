import pandas as pd
import os
import time
from colorama import init, Fore, Style
from exeomspxy import get_combined_data
import pytz
import subprocess  # <-- for triggering exesqrpxy.py
from datetime import datetime, time as dt_time

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
    """Calculates XX⚪YY and returns True if LTP >= Target.
    XX → difference of buy price to LTP, colored green if positive, red if negative.
    ⚪ → same color as XX.
    YY → distance to target, unchanged.
    """
    try:
        ltp = float(row.get("sell_prc", 0))
        tgt = float(row.get("pxy_tgt", 0))
        buy = float(row.get("buy_prc", 0))  # buy price

        if ltp <= 0: 
            return "00⚪00", False

        # XX = LTP - Buy Price
        to_buy = int(ltp - buy)
        to_tgt = min(99, max(0, int(tgt - ltp)))

        # Color based on profit/loss
        color = Fore.GREEN if to_buy > 0 else Fore.RED if to_buy < 0 else Fore.WHITE

        buy_s, tg_s = f"{abs(to_buy):02d}", f"{to_tgt:02d}"

        is_hit = ltp >= tgt

        # ⚪ takes the same color as XX
        return f"{color}{buy_s}{color}⚪{Fore.RESET}{tg_s}", is_hit
    except:
        return "00⚪00", False

def run_snapshot():
    # --- IST Time Check for Auto Exit ---
    IST = pytz.timezone("Asia/Kolkata")
    now = datetime.now(IST).time()
    exit_start = dt_time(15, 19)  # 3:19 PM
    exit_end   = dt_time(15, 30)  # 3:30 PM

    if exit_start <= now < exit_end:
        print(f"{Fore.YELLOW}⚡ Exit Window Active! Triggering exesqrpxy.py ⚡")
        try:
            subprocess.run(["python3", "exesqrpxy.py"], check=True)
        except Exception as e:
            print(f"{Fore.RED}❌ Failed to run exesqrpxy.py: {e}")

    # --- Original Functionality ---
    data = get_combined_data()
    df = data.get("active_orders", pd.DataFrame())
    
    from runclntpxy import get_session
    client = get_session()

    if df.empty:
        print(f"{Fore.YELLOW}No active orders. System idling...{Fore.RESET}")
        return

    # 40-char GRID: SYM(15) ST(12) PNL(10) ~ total 40
    header = f"{'SYM':<18}{'ST':^12}{'PNL':>7}"
    print(f"{Fore.CYAN}{Style.BRIGHT}{header}")
    print("-" * 40)

    for _, r in df.iterrows():
        raw_sym = str(r.get('symbol',''))
        sym = raw_sym.replace("NIFTY26", "")[:15]
        
        st_display, is_target_hit = compute_st_fixed(r)
        if is_target_hit:
            place_exit_order(client, r)
        
        pnl = int(r.get('pnl', 0))
        p_col = Fore.GREEN if pnl > 0 else Fore.RED if pnl < 0 else Fore.WHITE
        
        # Print only symbol, ST, PNL
        print(f"{sym:<21}{st_display:^12}{p_col}{pnl:>10}")
    
    print("-" * 40)
    print(f"{Fore.WHITE}Refreshed: {time.strftime('%H:%M:%S')}")

if __name__ == "__main__":
    run_snapshot()
