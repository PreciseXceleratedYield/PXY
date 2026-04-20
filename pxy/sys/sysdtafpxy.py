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
    KOTAK NEO V2 - QUOTES OHLC FETCH
    Hard-coded: nse_cm, quote_type="ohlc"
    """
    ticker_symbol = ticker or TICKER

    try:
        client = get_session()

        # FETCH CURRENT QUOTE
        # For Nifty 50, use the exact string name as the token
        instr_tokens = [{"instrument_token": ticker_symbol, "exchange_segment": "nse_cm"}]
        
        # Note: 'isIndex' is removed here as your previous version failed with it
        response = client.quotes(instrument_tokens=instr_tokens, quote_type="ohlc")

        # LOGIC FIX: The SDK returns a dictionary where "data" contains a LIST of scripts
        if response and "data" in response and isinstance(response["data"], list):
            data_list = response["data"]
            if not data_list:
                return pd.DataFrame()
            
            # The actual OHLC data is nested inside the 'ohlc' key of the first item
            raw = data_list[0]
            ohlc = raw.get("ohlc", {})
            
            # Use ltp (Last Traded Price) if close is not yet finalized
            ltp = float(raw.get("last_traded_price", 0))
            
            df = pd.DataFrame([{
                "Datetime": datetime.now().replace(second=0, microsecond=0),
                "Open": float(ohlc.get("open", ltp)),
                "High": float(ohlc.get("high", ltp)),
                "Low": float(ohlc.get("low", ltp)),
                "Close": ltp,
                "Volume": float(raw.get("volume", 0))
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
        # Debugging step: print the full response if empty to see why
        print("No data received. Try adding 'isIndex=True' back if this still fails.")



