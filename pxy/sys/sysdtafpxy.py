# sysdtafpxy.py

import sys
import os
import pandas as pd
from datetime import datetime, timedelta

# ---------------- PATH MANAGEMENT ----------------
# Matches: /home/neo/pxy/sys/exe/run/
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__)) 
RUN_DIR = os.path.join(CURRENT_DIR, "exe", "run")

if RUN_DIR not in sys.path:
    sys.path.append(RUN_DIR)

# Import dependencies
from syscnfgpxy import TICKER
from runclntpxy import get_session

def fetch_yf_data(ticker=None):
    """
    KOTAK NEO - HARD-CODED FETCH
    Updated to use 'historical_data' method.
    """
    ticker_symbol = ticker or TICKER

    try:
        client = get_session()

        # Date range: Today and Yesterday
        to_date = datetime.now().strftime("%d-%m-%Y")
        from_date = (datetime.now() - timedelta(days=1)).strftime("%d-%m-%Y")

        # API CALL - Switched 'history' to 'historical_data'
        # Hard-coded: nse_cm, 1minute, isIndex=True
        response = client.historical_data(
            instrument_token=ticker_symbol,
            exchange_segment="nse_cm",
            interval="1minute",
            from_date=from_date,
            to_date=to_date,
            isIndex=True
        )

        if response and "data" in response:
            df = pd.DataFrame(response["data"])
            
            # Standardization mapping
            rename_map = {
                "time": "Datetime", 
                "open": "Open", 
                "high": "High",
                "low": "Low", 
                "close": "Close", 
                "volume": "Volume"
            }
            df.rename(columns=rename_map, inplace=True)
            
            if "Datetime" in df.columns:
                df["Datetime"] = pd.to_datetime(df["Datetime"])
            
            return df.dropna().reset_index(drop=True)
            
        print(f"NEO_EMPTY_OR_UNAUTHORIZED|{ticker_symbol}")
        return pd.DataFrame()

    except Exception as e:
        print(f"NEO_FETCH_ERROR|{ticker_symbol}|{str(e)}")
        return pd.DataFrame()

def get_latest_data():
    df = fetch_yf_data()
    return df.tail(1) if not df.empty else pd.DataFrame()

if __name__ == "__main__":
    print(f"Ticker: {TICKER} | Segment: nse_cm | Interval: 1minute")
    data = fetch_yf_data()
    if not data.empty:
        print("SUCCESS! DATA RECEIVED:")
        print(data.tail(5))
    else:
        print("Check if your account has 'Historical Data' enabled in Neo portal.")
