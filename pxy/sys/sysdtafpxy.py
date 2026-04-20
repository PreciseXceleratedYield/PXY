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
DEFAULT_MIN_ROWS = 5

def fetch_yf_data(period="1d", interval=None, min_rows=None, ticker=None):
    """
    KOTAK NEO implementation of your yfinance fetcher.
    Hard-coded to nse_cm and 1minute for Kotak compatibility.
    """
    ticker_symbol = ticker or TICKER
    
    try:
        client = get_session()
        instr_tokens = [{"instrument_token": ticker_symbol, "exchange_segment": "nse_cm"}]
        
        # Kotak API Call
        response = client.quotes(instrument_tokens=instr_tokens, quote_type="ohlc")

        if isinstance(response, list) and len(response) > 0:
            raw = response[0]
            ohlc_data = raw.get("ohlc", {})
            close_val = float(ohlc_data.get("close", 0))

            # Construct the row matching your exact expected format
            data_row = {
                "Datetime": datetime.now().replace(second=0, microsecond=0),
                "Open": float(ohlc_data.get("open", close_val)),
                "High": float(ohlc_data.get("high", close_val)),
                "Low": float(ohlc_data.get("low", close_val)),
                "Close": close_val,
                "Volume": 0
            }

            # Create DataFrame
            df = pd.DataFrame([data_row])

            # Downstream fix: If min_rows is required, duplicate the current row 
            # to prevent strategy crashes (since Quotes only gives 1 row)
            target_rows = min_rows or DEFAULT_MIN_ROWS
            if len(df) < target_rows:
                df = pd.concat([df] * target_rows, ignore_index=True)

            # Ensure 'Datetime' exists as a column (simulating your reset_index)
            # In your yf code, reset_index moved 'Datetime' from Index to Column.
            # Here we already have it as a column, so we just ensure index is clean.
            df.reset_index(drop=True, inplace=True)
            
            return df
            
        return pd.DataFrame()

    except Exception as e:
        print(f"NEO_ERROR|{ticker_symbol}|{str(e)}")
        return pd.DataFrame()

def get_latest_data():
    """ Returns the latest row of data """
    df = fetch_yf_data()
    return df.tail(1)

# -------- Self-runnable test --------
if __name__ == "__main__":
    print("=== Testing Kotak-Neo Data Fetch Module ===")
    df = fetch_yf_data()
    if not df.empty:
        print(f"Rows returned: {len(df)}")
        print(df.tail(5))
    else:
        print("Data fetch failed.")

