# exesqrpxy.py
import pandas as pd
from runclntpxy import get_session
from exeomspxy import get_combined_data
from colorama import Fore, Style, init

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
    client = get_session()
    if not client:
        print(f"{Fore.RED}❌ Session not initialized. Exiting...")
        return

    data = get_combined_data()
    df = data.get("active_orders", pd.DataFrame())

    if df.empty:
        print(f"{Fore.YELLOW}No active positions to exit.{Fore.RESET}")
        return

    for _, row in df.iterrows():
        symbol = row.get("symbol")
        qty    = row.get("qty", 0)
        if symbol and qty != 0:
            place_exit_order(client, symbol, qty)

    print(f"{Fore.GREEN}{Style.BRIGHT}✅ All positions exit attempted.")

if __name__ == "__main__":
    exit_all_positions()
