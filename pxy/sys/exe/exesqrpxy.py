import sys
import os

# Add the 'run' subfolder of the current script to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))  # .../pxy/sys/exe
run_dir = os.path.join(current_dir, "run")               # .../pxy/sys/exe/run
sys.path.append(run_dir)

# Now Python can find runclntpxy
from runclntpxy import get_session

import pandas as pd
from exeomspxy import get_combined_data
from colorama import Fore, Style, init
import pytz
from datetime import datetime, time as dt_time

init(autoreset=True)

def place_exit_order(client, symbol, qty):
    try:
        params = {
            "exchange_segment": "nse_fo",
            "product": "NRML",
            "price": "0",
            "order_type": "MKT",
            "quantity": str(abs(int(qty))),
            "validity": "DAY",
            "trading_symbol": str(symbol),
            "transaction_type": "S",
            "amo": "NO",
            "disclosed_quantity": "0",
            "market_protection": "0"
        }
        print(f"{Fore.MAGENTA}{Style.BRIGHT}⚡ EXITING POSITION: {symbol} Qty: {qty}")
        return client.place_order(**params)
    except Exception as e:
        print(f"{Fore.RED}❌ Exit Order Error for {symbol}: {e}")
        return None

def exit_all_positions():
    IST = pytz.timezone("Asia/Kolkata")
    now = datetime.now(IST).time()
    client = get_session()
    if not client:
        print(f"{Fore.RED}❌ Session not initialized. Exiting...")
        return

    data = get_combined_data()
    active_df = data.get("active_orders", pd.DataFrame())
    market_df = data.get("market_snapshot", pd.DataFrame())

    if active_df.empty:
        print(f"{Fore.YELLOW}No active positions to exit.{Fore.RESET}")
        return

    direction = market_df["direction"].iloc[-1] if not market_df.empty and "direction" in market_df.columns else None
    exit_all_after = dt_time(15, 25)  # 3:25 PM

    for _, row in active_df.iterrows():
        symbol = row.get("symbol")
        qty = row.get("qty", 0)
        if not symbol or qty == 0:
            continue

        if now < exit_all_after:
            if direction == "UP" and "PE" in symbol:
                place_exit_order(client, symbol, qty)
            elif direction == "DOWN" and "CE" in symbol:
                place_exit_order(client, symbol, qty)
            else:
                print(f"{Fore.CYAN}Holding {symbol} | Direction: {direction}")
        else:
            place_exit_order(client, symbol, qty)

    print(f"{Fore.GREEN}{Style.BRIGHT}✅ Exit attempt completed.")

if __name__ == "__main__":
    exit_all_positions()
