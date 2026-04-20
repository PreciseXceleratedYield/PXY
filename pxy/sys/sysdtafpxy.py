# sysdtafpxy.py
import sys, os
import pandas as pd
from datetime import datetime

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
        instr_tokens = [{"instrument_token": ticker_symbol, "exchange_segment": "nse_cm"}]
        
        # API Call
        response = client.quotes(instrument_tokens=instr_tokens, quote_type="ohlc")

        # PARSING LOGIC: Your version returns a list of dicts directly
        if isinstance(response, list) and len(response) > 0:
            raw = response[0]  # Get the first dictionary in the list
            ohlc_data = raw.get("ohlc", {})
            
            # Use 'close' as LTP since the API is providing it in the ohlc block
            close_val = float(ohlc_data.get("close", 0))

            df = pd.DataFrame([{
                "Datetime": datetime.now().replace(second=0, microsecond=0),
                "Open": float(ohlc_data.get("open", close_val)),
                "High": float(ohlc_data.get("high", close_val)),
                "Low": float(ohlc_data.get("low", close_val)),
                "Close": close_val,
                "Volume": 0.0  # Indices usually don't return volume in this block
            }])
            return df
            
        return pd.DataFrame()

    except Exception as e:
        print(f"NEO_CRITICAL_ERR|{ticker_symbol}|{str(e)}")
        return pd.DataFrame()

def get_latest_data():
    return fetch_yf_data()

if __name__ == "__main__":
    data = fetch_yf_data()
    if not data.empty:
        print("SUCCESS! NIFTY DATA PARSED:")
        print(data)
    else:
        print("Parsing failed. Check response structure.")

