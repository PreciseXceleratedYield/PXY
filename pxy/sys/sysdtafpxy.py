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
    Uses 'quotes' method to fetch OHLC because 'history' is often restricted.
    """
    ticker_symbol = ticker or TICKER

    try:
        client = get_session()

        # FETCH CURRENT QUOTE (Hard-coded for OHLC)
        # Standard method name in V2 is client.quotes()
        instr_tokens = [{"instrument_token": ticker_symbol, "exchange_segment": "nse_cm"}]
        response = client.quotes(instrument_tokens=instr_tokens, quote_type="ohlc", isIndex=True)

        if response and "data" in response and len(response["data"]) > 0:
            raw_data = response["data"][0]
            
            # Format into a DataFrame compatible with your strategy
            df = pd.DataFrame([{
                "Datetime": datetime.now().replace(second=0, microsecond=0),
                "Open": float(raw_data.get("open", 0)),
                "High": float(raw_data.get("high", 0)),
                "Low": float(raw_data.get("low", 0)),
                "Close": float(raw_data.get("ltp", raw_data.get("close", 0))),
                "Volume": float(raw_data.get("v", 0))
            }])
            
            return df
            
        print(f"NEO_QUOTE_EMPTY|{ticker_symbol}")
        return pd.DataFrame()

    except Exception as e:
        print(f"NEO_CRITICAL_ERR|{ticker_symbol}|{str(e)}")
        return pd.DataFrame()

def get_latest_data():
    """Returns the current 1-minute OHLC bar."""
    return fetch_yf_data()

if __name__ == "__main__":
    print(f"Ticker: {TICKER} | Exchange: nse_cm | Mode: Live Quote OHLC")
    data = fetch_yf_data()
    if not data.empty:
        print("CURRENT BAR DATA:")
        print(data)



