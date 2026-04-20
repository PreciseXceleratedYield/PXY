# sysdtafpxy.py
import sys
import os
import pandas as pd
from datetime import datetime, timedelta

# ---------------- FIXED PATH MANAGEMENT ----------------
# Based on your 'ls' output: /home/neo/pxy/sys/exe/run/
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__)) 
RUN_DIR = os.path.join(CURRENT_DIR, "exe", "run")

if RUN_DIR not in sys.path:
    sys.path.append(RUN_DIR)

# Safety Check
if not os.path.exists(os.path.join(RUN_DIR, "runclntpxy.py")):
    print(f"CRITICAL: runclntpxy.py STILL NOT FOUND IN: {RUN_DIR}")

# Now safe to import
from syscnfgpxy import TICKER
from runclntpxy import get_session

# ---------------- FETCH DATA FUNCTION (HARD-CODED) ----------------
def fetch_yf_data(ticker=None):
    """
    KOTAK NEO V2 - FULL HARD-CODED FETCH
    Enforces: Exchange="nse_cm", Interval="1minute", isIndex=True
    """
    ticker_symbol = ticker or TICKER

    try:
        client = get_session()

        # Hard-coded backfill range: Last 1 day
        to_date = datetime.now().strftime("%d-%m-%Y")
        from_date = (datetime.now() - timedelta(days=1)).strftime("%d-%m-%Y")

        # EVERYTHING HARD-CODED EXCEPT ticker_symbol
        response = client.history(
            instrument_token=ticker_symbol,
            exchange_segment="nse_cm",  # Hard-coded
            interval="1minute",         # Hard-coded
            from_date=from_date,
            to_date=to_date,
            isIndex=True                # Hard-coded for Nifty index
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
            
        print(f"NEO_EMPTY_RESPONSE|{ticker_symbol}")
        return pd.DataFrame()

    except Exception as e:
        print(f"NEO_CRITICAL_ERR|{ticker_symbol}|{str(e)}")
        return pd.DataFrame()

def get_latest_data():
    df = fetch_yf_data()
    return df.tail(1) if not df.empty else pd.DataFrame()

if __name__ == "__main__":
    print(f"Ticker: {TICKER} | Exchange: nse_cm | Interval: 1minute")
    data = fetch_yf_data()
    if not data.empty:
        print("SUCCESS! LAST 5 CANDLES:")
        print(data.tail(5))

