import sys, os, warnings
import pandas as pd
from datetime import datetime
from syscnfgpxy import TICKER

# Silence warnings to keep downstream logs clean
warnings.simplefilter(action='ignore', category=FutureWarning)

# ---------------- PATH MANAGEMENT ----------------
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__)) 
RUN_DIR = os.path.join(CURRENT_DIR, "exe", "run")
if RUN_DIR not in sys.path: sys.path.append(RUN_DIR)

from runclntpxy import get_session

# --- CONFIGURATION (Matches Downstream) ---
CSV_FILE = f"{TICKER.lower().replace(' ', '_')}_history.csv"
DEFAULT_MIN_ROWS = 50 

def fetch_yf_data(period="1d", interval="1m", min_rows=None, ticker=None):
    """
    KOTAK NEO REPLACEMENT:
    1. Updates CSV with true 1-minute OHLC.
    2. Filters for today's data only.
    3. Returns exactly 50 rows from the CSV.
    """
    t = ticker or TICKER
    target_rows = min_rows or DEFAULT_MIN_ROWS
    now = datetime.now()
    today_str = now.strftime("%Y-%m-%d")
    current_min = now.strftime("%Y-%m-%d %H:%M:00")
    
    try:
        # --- 1. RUN: FETCH LIVE LTP ---
        client = get_session()
        instr_tokens = [{"instrument_token": t, "exchange_segment": "nse_cm"}]
        response = client.quotes(instrument_tokens=instr_tokens, quote_type="ltp")
        
        # FIX: Access the dictionary inside the Neo list response
        if isinstance(response, list) and len(response) > 0:
            raw = response[0] # Grab the first item in the list
        else:
            raw = {}

        # Capture Index Value or Last Traded Price
        ltp = float(raw.get("last_traded_price", raw.get("ltp", raw.get("iv", 0))))

        if ltp > 0:
            # --- 2. UPDATE: MANAGE CSV HISTORY (Today Only) ---
            if os.path.exists(CSV_FILE):
                df_hist = pd.read_csv(CSV_FILE)
                df_hist['Datetime'] = pd.to_datetime(df_hist['Datetime'])
                # Keep only Today's data
                df_hist = df_hist[df_hist['Datetime'].dt.strftime('%Y-%m-%d') == today_str]
            else:
                df_hist = pd.DataFrame(columns=["Datetime", "Open", "High", "Low", "Close", "Volume"])

            live_dt = pd.to_datetime(current_min)
            if not df_hist.empty and df_hist['Datetime'].iloc[-1] == live_dt:
                # SAME MINUTE: Build OHLC dynamically from LTP
                idx = df_hist.index[-1]
                df_hist.at[idx, 'High'] = max(float(df_hist.at[idx, 'High']), ltp)
                df_hist.at[idx, 'Low'] = min(float(df_hist.at[idx, 'Low']), ltp)
                df_hist.at[idx, 'Close'] = ltp
            else:
                # NEW MINUTE: Start fresh candle with LTP
                new_row = {"Datetime": current_min, "Open": ltp, "High": ltp, "Low": ltp, "Close": ltp, "Volume": 0}
                df_hist = pd.concat([df_hist, pd.DataFrame([new_row])], ignore_index=True)
            
            # Save CSV (Update File)
            df_hist.to_csv(CSV_FILE, index=False)
        
        # --- 3. READ: RETURN DATA FROM FILE ---
        if os.path.exists(CSV_FILE):
            df = pd.read_csv(CSV_FILE)
            df['Datetime'] = pd.to_datetime(df['Datetime'])
            
            # Backfill padding to 50 rows if history is short (Early morning)
            if len(df) < target_rows:
                # Use current data for padding
                last_row = df.iloc[-1].to_dict() if not df.empty else {"Datetime": current_min, "Open": ltp, "High": ltp, "Low": ltp, "Close": ltp, "Volume": 0}
                padding = pd.DataFrame([last_row] * (target_rows - len(df)))
                df = pd.concat([padding, df], ignore_index=True)

            return df.tail(target_rows).reset_index(drop=True)
        
        return pd.DataFrame()

    except Exception as e:
        print(f"NEO_DATA_ERROR|{e}")
        return pd.DataFrame()

def get_latest_data():
    """ Returns the single latest row of data """
    return fetch_yf_data().tail(1)

if __name__ == "__main__":
    print(f"=== Kotak Neo Sync: {TICKER} (Real-time OHLC) ===")
    df = fetch_yf_data()
    if not df.empty:
        print(df.tail(5))



