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
        
        # 1. Removed 'isIndex' entirely to stop the Crash
        # 2. Using quote_type="ohlc"
        response = client.quotes(instrument_tokens=instr_tokens, quote_type="ohlc")

        # --- DEBUG PRINT: SEE WHAT KOTAK IS ACTUALLY SAYING ---
        # print(f"RAW_RESPONSE: {response}")

        if response and "data" in response:
            data_list = response["data"]
            
            # Neo sometimes returns a list, sometimes a single dict depending on version
            raw = data_list[0] if isinstance(data_list, list) and data_list else data_list
            
            if not raw or "ohlc" not in raw:
                # If 'ohlc' key is missing, the ticker name might be wrong for your segment
                return pd.DataFrame()
            
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
    print(f"Ticker: {TICKER} | Mode: Quotes OHLC (Jhatrd)")
    data = fetch_yf_data()
    if not data.empty:
        print("SUCCESS! DATA:")
        print(data)
    else:
        print("EMPTY DATA: Uncomment 'print(f\"RAW_RESPONSE: {response}\")' in the code to see the error from Kotak.")
