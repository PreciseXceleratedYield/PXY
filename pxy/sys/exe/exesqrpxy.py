# exesqrpxy.py
import pandas as pd
from runclntpxy import get_session
from exeomspxy import get_combined_data
from colorama import Fore, Style, init
import pytz
from datetime import datetime, time as dt_time

init(autoreset=True)

def place_exit_order(client, symbol, qty):
    """Exits position via Market Sell."""
    try:
        params = {
            "exchange_segment": "nse_fo",
            "product": "NRML",
            "price": "0",
            "order_type": "MKT",
            "quantity": str(abs(int(qty))),
            "validity": "DAY",
            "trading_symbol": str(symbol),
            "transaction_type": "S",  # Sell to exit
            "amo": "NO",
            "disclosed_quantity": "0",
            "market_protection": "0"
        }
        print(f"{Fore.MAGENTA}{Style.BRIGHT}⚡ EXITING POSITION: {symbol} Qty: {qty}")
        res = client.place_order(**params)
        return res
    except Exception as e:
        print(f"{Fore.RED}❌ Exit Order Error for {symbol}: {e}")
        return None

def exit_all_positions():
    IST = pytz.timezone("Asia/Kolkata")
    now = datetime.now(IST).time()
    client = get_session()
    if not client:
        print(f"{Fore.RED}❌ Session not initialized. Exiting..."); return

    data = get_combined_data()
    active_df = data.get("active_orders", pd.DataFrame())
    market_df = data.get("market_snapshot", pd.DataFrame())

    if active_df.empty:
        print(f"{Fore.YELLOW}No active positions to exit.{Fore.RESET}")
        return

    # Get the latest market direction
    direction = None
    if not market_df.empty and "direction" in market_df.columns:
        direction = market_df["direction"].iloc[-1]  # 'UP' or 'DOWN'

    # Define the hard exit time threshold
    exit_all_after = dt_time(15, 25)  # 3:25 PM

    for _, row in active_df.iterrows():
        symbol = row.get("symbol")
        qty    = row.get("qty", 0)
        if not symbol or qty == 0:
            continue

        # --- Direction-aware exit before 3:25 PM ---
        if now < exit_all_after:
            if direction == "UP" and "PE" in symbol:
                place_exit_order(client, symbol, qty)
            elif direction == "DOWN" and "CE" in symbol:
                place_exit_order(client, symbol, qty)
            else:
                print(f"{Fore.CYAN}Holding {symbol} | Direction: {direction}")
        else:
            # --- After 3:25 PM: exit all positions ---
            place_exit_order(client, symbol, qty)

    print(f"{Fore.GREEN}{Style.BRIGHT}✅ Exit attempt completed.")

if __name__ == "__main__":
    exit_all_positions()
