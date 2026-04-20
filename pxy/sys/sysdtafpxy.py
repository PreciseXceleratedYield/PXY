# sysdtafpxy.py
import sys
import os
import pandas as pd
from datetime import datetime, timedelta

# ---------------- FIXED PATH MANAGEMENT ----------------
# Get the absolute path of the 'pxy' directory
# From /home/neo/V1L58/pxy/sys/sysdtafpxy.py, we need to go up one level
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__)) # /home/neo/V1L58/pxy/sys
BASE_DIR = os.path.dirname(CURRENT_DIR)                 # /home/neo/V1L58/pxy

# Now target the run directory relative to 'pxy'
RUN_DIR = os.path.join(BASE_DIR, "exe", "run")

if RUN_DIR not in sys.path:
    sys.path.append(RUN_DIR)

# Safety check: Verify the file actually exists where we expect it
if not os.path.exists(os.path.join(RUN_DIR, "runclntpxy.py")):
    print(f"CRITICAL: runclntpxy.py NOT found in {RUN_DIR}")

# Now safe to import
try:
    from syscnfgpxy import TICKER
    from runclntpxy import get_session
except ModuleNotFoundError as e:
    print(f"STILL MISSING: {e}. Check if runclntpxy.py is inside /home/neo/V1L58/pxy/exe/run/")
    sys.exit(1)

# ---------------- FETCH DATA FUNCTION (HARD-CODED) ----------------
def fetch_yf_data(ticker=None):
    ticker_symbol = ticker or TICKER
    try:
        client = get_session()
        to_date = datetime.now().strftime("%d-%m-%Y")
        from_date = (datetime.now() - timedelta(days=1)).strftime("%d-%m-%Y")

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
        return pd.DataFrame()
    except Exception as e:
        print(f"NEO_FETCH_ERROR|{ticker_symbol}|{str(e)}")
        return pd.DataFrame()

def get_latest_data():
    df = fetch_yf_data()
    return df.tail(1) if not df.empty else pd.DataFrame()

if __name__ == "__main__":
    print(f"Running fetch for: {TICKER}")
    data = fetch_yf_data()
    if not data.empty:
        print(data.tail(5))


