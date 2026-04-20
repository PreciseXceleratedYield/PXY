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
    Hard-coded: nse_cm, quote_type="ohlc", isIndex=True
    """
    # Use config TICKER if none provided (Ensure it is "Nifty 50")
    ticker_symbol = ticker or TICKER

    try:
        client = get_session()

        # Token list - Nifty 50 requires exact string name
        instr_tokens = [{"instrument_token": ticker_symbol, "exchange_segment": "nse_cm"}]
        
        # Calling quotes with isIndex=True (Required for string-based index tokens)
        response = client.quotes(instrument_tokens=instr_tokens, quote_type="ohlc", isIndex=True)

        # DEBUG: Uncomment the line below to see the raw API output if data is still missing
        # print(f"DEBUG RESPONSE: {response}")

        if response and "data" in response:
            data_list = response["data"]
            if not data_list or len(data_list) == 0:
                return pd.DataFrame()
            
            # The structure often puts the scrip data in the first list item
            raw = data_list[0] 
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
    print(f"Ticker: {TICKER} | Segment: nse_cm | Mode: Quotes OHLC")
    data = fetch_yf_data()
    if not data.empty:
        print("SUCCESS! CURRENT CANDLE:")
        print(data)
    else:
        print("Still no data. Ensure Market is open (9:15 AM - 3:30 PM) and 'Nifty 50' is correctly spelled in syscnfgpxy.py.")
