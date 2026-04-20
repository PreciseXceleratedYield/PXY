# sysdtafpxy.py

import sys
import os
import pandas as pd
from datetime import datetime, timedelta

# ---------------- PATH MANAGEMENT ----------------
# Standardize paths to ensure runclntpxy can be imported from exe/run
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUN_DIR = os.path.join(BASE_DIR, "exe", "run")

if RUN_DIR not in sys.path:
    sys.path.append(RUN_DIR)

# Import ONLY ticker from config; session client from the run folder
from syscnfgpxy import TICKER
from runclntpxy import get_session

def fetch_yf_data(ticker=None):
    """
    KOTAK NEO V2 - FULL HARD-CODED FETCH
    Enforces: Exchange="nse_cm", Interval="1minute", isIndex=True
    """
    # Only ticker remains dynamic, falling back to config if not provided
    ticker_symbol = ticker or TICKER

    try:
        # Get active Kotak Neo session
        client = get_session()

        # Hard-coded Date Range: Fetching last 1 day for backfill
        to_date = datetime.now().strftime("%d-%m-%Y")
        from_date = (datetime.now() - timedelta(days=1)).strftime("%d-%m-%Y")

        # JHATRD (HARD-CODED) API CALL
        response = client.history(
            instrument_token=ticker_symbol,
            exchange_segment="nse_cm",  # HARD-CODED
            interval="1minute",         # HARD-CODED
            from_date=from_date,
            to_date=to_date,
            isIndex=True                # HARD-CODED (Required for Nifty 50)
        )

        # Process Response
        if response and "data" in response:
            df = pd.DataFrame(response["data"])
            
            # Internal Hard-coded Standardized Column Map
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
            
        print(f"NEO_EMPTY_RESPONSE|{ticker_symbol}")
        return pd.DataFrame()

    except Exception as e:
        print(f"NEO_CRITICAL_ERR|{ticker_symbol}|{str(e)}")
        return pd.DataFrame()

def get_latest_data():
    """
    Returns only the most recent hard-coded 1-minute candle.
    """
    df = fetch_yf_data()
    return df.tail(1) if not df.empty else pd.DataFrame()

# -------- TEST RUN --------
if __name__ == "__main__":
    print(f"Path Check: BASE={BASE_DIR} | RUN={RUN_DIR}")
    print(f"Starting hard-coded fetch for: {TICKER}")
    
    data = fetch_yf_data()
    
    if not data.empty:
        print("LAST 5 ROWS:")
        print(data.tail(5))
    else:
        print("FETCH FAILED. Check credentials or ticker string.")

