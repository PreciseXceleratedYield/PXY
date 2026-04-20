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

        # Build token list
        instr_tokens = [{"instrument_token": ticker_symbol, "exchange_segment": "nse_cm"}]
        
        # Fetching Quotes
        response = client.quotes(instrument_tokens=instr_tokens, quote_type="ohlc")

        # --- CRITICAL: LOOK AT THIS OUTPUT IN YOUR TERMINAL ---
        print(f"\n--- DEBUG RAW RESPONSE ---\n{response}\n--------------------------\n")

        if response and "data" in response:
            data_list = response["data"]
            
            # Neo SDK usually returns a list of dictionaries
            if isinstance(data_list, list) and len(data_list) > 0:
                raw = data_list[0] # Take first scrip result
                
                ohlc = raw.get("ohlc", {})
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

if __name__ == "__main__":
    print(f"Ticker: {TICKER} | Starting Fetch...")
    data = fetch_yf_data()
    if data is not None and not data.empty:
        print("SUCCESS! DATA RECEIVED.")
        print(data)
    else:
        print("STILL EMPTY. Please check the RAW_RESPONSE printed above.")

