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
    """
    KOTAK NEO V2 - QUOTES FALLBACK
    Hard-coded: nse_cm, quote_type="ohlc"
    """
    ticker_symbol = ticker or TICKER

    try:
        client = get_session()

        # FETCH CURRENT QUOTE
        # Note: isIndex is NOT a parameter for quotes()
        instr_tokens = [{"instrument_token": ticker_symbol, "exchange_segment": "nse_cm"}]
        response = client.quotes(instrument_tokens=instr_tokens, quote_type="ohlc")

        if response and "data" in response:
            # Neo response data is usually a list of dicts
            data_list = response["data"]
            if not data_list:
                return pd.DataFrame()
            
            raw = data_list[0] # Get first scrip result
            
            # Create DataFrame matching your strategy columns
            df = pd.DataFrame([{
                "Datetime": datetime.now().replace(second=0, microsecond=0),
                "Open": float(raw.get("open", 0)),
                "High": float(raw.get("high", 0)),
                "Low": float(raw.get("low", 0)),
                "Close": float(raw.get("ltp", raw.get("close", 0))),
                "Volume": float(raw.get("v", 0))
            }])
            
            return df
            
        return pd.DataFrame()

    except Exception as e:
        print(f"NEO_CRITICAL_ERR|{ticker_symbol}|{str(e)}")
        return pd.DataFrame()

def get_latest_data():
    return fetch_yf_data()

if __name__ == "__main__":
    print(f"Ticker: {TICKER} | Segment: nse_cm | Mode: Live Quote OHLC")
    data = fetch_yf_data()
    if not data.empty:
        print("CURRENT BAR DATA:")
        print(data)
    else:
        print("No data received. Check if Market is Open or Ticker is correct.")


