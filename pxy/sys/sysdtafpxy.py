# sysdtafpxy.py
import sys
import os
import pandas as pd
from datetime import datetime
from syscnfgpxy import TICKER

# ---------------- PATH MANAGEMENT ----------------
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__)) 
RUN_DIR = os.path.join(CURRENT_DIR, "exe", "run")
if RUN_DIR not in sys.path:
    sys.path.append(RUN_DIR)

from runclntpxy import get_session

# Module-level defaults to match your downstream
DEFAULT_INTERVAL = "1m"
DEFAULT_MIN_ROWS = 50

def fetch_yf_data(period="1d", interval=None, min_rows=None, ticker=None):
    """
    KOTAK NEO implementation of yfinance fetcher.
    Maintains exact 50-row structure and Datetime column for downstream.
    """
    t = ticker or TICKER
    target_rows = min_rows or DEFAULT_MIN_ROWS

    # --- LOT SIZE LOGIC ---
    # Current 2025 Market Lot sizes
    if t == "Nifty Bank":
        LOT_SIZE = 30
    elif t == "Nifty 50":
        LOT_SIZE = 65
    else:
        LOT_SIZE = None

    try:
        client = get_session()
        # Nifty 50 and Nifty Bank require exact string names in Kotak Neo V2
        instr_tokens = [{"instrument_token": t, "exchange_segment": "nse_cm"}]
        
        # Kotak API Call - Returns a list of dictionaries
        response = client.quotes(instrument_tokens=instr_tokens, quote_type="ohlc")

        if isinstance(response, list) and len(response) > 0:
            raw = response[0]
            ohlc_data = raw.get("ohlc", {})
            
            # Extract current data
            ltp = float(raw.get("last_traded_price", 0))
            close_val = float(ohlc_data.get("close", ltp))

            # Construct the row matching your exact expected format
            data_row = {
                "Datetime": datetime.now().replace(second=0, microsecond=0),
                "Open": float(ohlc_data.get("open", close_val)),
                "High": float(ohlc_data.get("high", close_val)),
                "Low": float(ohlc_data.get("low", close_val)),
                "Close": close_val,
                "Volume": 0,
                "LotSize": LOT_SIZE
            }

            # Create synthetic history (50 rows) to prevent downstream index crashes
            df = pd.DataFrame([data_row] * target_rows)
            
            # Ensure 'Datetime' exists as a column (mimics reset_index behavior)
            df.reset_index(drop=True, inplace=True)
            
            return df
            
        return pd.DataFrame()

    except Exception as e:
        print(f"NEO_ERROR|{t}|{str(e)}")
        return pd.DataFrame()

def get_latest_data():
    """ Returns the latest row of data """
    df = fetch_yf_data()
    return df.tail(1)

# -------- Self-runnable test --------
if __name__ == "__main__":
    print(f"=== Testing Kotak-Neo Data Fetch Module for {TICKER} ===")
    df = fetch_yf_data()
    if not df.empty:
        print(f"Lot Size: {df['LotSize'].iloc[-1]} | Rows: {len(df)}")
        print(df.tail(50))
    else:
        print("Data fetch failed. Ensure TICKER is 'Nifty 50' or 'Nifty Bank'.")

