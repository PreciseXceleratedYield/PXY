# sysdtafpxy.py
import sys, os
import pandas as pd
from datetime import datetime, timedelta

# --- PATH MANAGEMENT ---
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__)) 
RUN_DIR = os.path.join(CURRENT_DIR, "exe", "run")
if RUN_DIR not in sys.path: sys.path.append(RUN_DIR)

from syscnfgpxy import TICKER
from runclntpxy import get_session

def fetch_yf_data(ticker=None):
    ticker_symbol = ticker or TICKER
    try:
        client = get_session()

        # --- DEBUG: Print available methods to see what your version supports ---
        # print("Available methods:", [m for m in dir(client) if not m.startswith('_')])

        # Dates for backfill
        to_date = datetime.now().strftime("%d-%m-%Y")
        from_date = (datetime.now() - timedelta(days=1)).strftime("%d-%m-%Y")

        # Official V2 call (requires latest GitHub version)
        # Note: If this still fails, try 'get_history' or 'historical_data'
        response = client.history(
            instrument_token=ticker_symbol,
            exchange_segment="nse_cm",
            interval="1minute",
            from_date=from_date,
            to_date=to_date,
            isIndex=True
        )

        if response and "data" in response:
            df = pd.DataFrame(response["data"])
            rename_map = {"time": "Datetime", "open": "Open", "high": "High",
                          "low": "Low", "close": "Close", "volume": "Volume"}
            df.rename(columns=rename_map, inplace=True)
            if "Datetime" in df.columns:
                df["Datetime"] = pd.to_datetime(df["Datetime"])
            return df.dropna().reset_index(drop=True)
            
        print(f"EMPTY_OR_UNAUTHORIZED|{ticker_symbol}")
        return pd.DataFrame()

    except Exception as e:
        print(f"FETCH_CRITICAL_ERR|{ticker_symbol}|{str(e)}")
        return pd.DataFrame()

if __name__ == "__main__":
    print(f"Ticker: {TICKER} | Exchange: nse_cm | Interval: 1minute")
    data = fetch_yf_data()
    if not data.empty: print(data.tail(5))


