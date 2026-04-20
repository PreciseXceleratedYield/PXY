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

# --- CONFIGURATION ---
CSV_FILE = f"{TICKER.lower().replace(' ', '_')}_history.csv"
DEFAULT_MIN_ROWS = 50

def get_lot_size(t):
    if t == "Nifty Bank": return 30
    if t == "Nifty 50": return 75
    return None

def fetch_yf_data(ticker=None, min_rows=DEFAULT_MIN_ROWS):
    """
    1. Fetch Live Quote.
    2. Overwrite latest minute if timestamp matches, else append.
    3. Return 'min_rows' to downstream.
    """
    t = ticker or TICKER
    now = datetime.now()
    today_str = now.strftime("%Y-%m-%d")
    current_min = now.strftime("%Y-%m-%d %H:%M:00")
    
    try:
        # --- 1. RUN: FETCH LIVE QUOTE ---
        client = get_session()
        instr_tokens = [{"instrument_token": t, "exchange_segment": "nse_cm"}]
        response = client.quotes(instrument_tokens=instr_tokens, quote_type="ohlc")
        
        live_row = None
        if isinstance(response, list) and len(response) > 0:
            raw = response[0]
            ohlc = raw.get("ohlc", {})
            ltp = float(raw.get("last_traded_price", 0))
            
            live_row = {
                "Datetime": current_min,
                "Open": float(ohlc.get("open", ltp)),
                "High": float(ohlc.get("high", ltp)),
                "Low": float(ohlc.get("low", ltp)),
                "Close": ltp if ltp > 0 else float(ohlc.get("close", 0)),
                "Volume": 0,
                "LotSize": get_lot_size(t)
            }

        # --- 2. UPDATE: READ & CLEAN (TODAY ONLY) ---
        if os.path.exists(CSV_FILE):
            df_hist = pd.read_csv(CSV_FILE)
            df_hist['Datetime'] = pd.to_datetime(df_hist['Datetime'])
            df_hist = df_hist[df_hist['Datetime'].dt.strftime('%Y-%m-%d') == today_str]
        else:
            df_hist = pd.DataFrame()

        # --- 3. OVERWRITE LATEST OR APPEND ---
        if live_row:
            live_dt = pd.to_datetime(current_min)
            if not df_hist.empty and df_hist['Datetime'].iloc[-1] == live_dt:
                # Overwrite existing row for the same minute
                for key, val in live_row.items():
                    df_hist.iloc[-1, df_hist.columns.get_loc(key)] = val
            else:
                # Append new minute
                df_hist = pd.concat([df_hist, pd.DataFrame([live_row])], ignore_index=True)
            
            df_hist.to_csv(CSV_FILE, index=False)

        # --- 4. READ & BACKFILL ---
        if len(df_hist) < min_rows:
            fill_data = live_row if live_row else df_hist.iloc[-1].to_dict()
            padding = pd.DataFrame([fill_data] * (min_rows - len(df_hist)))
            df_hist = pd.concat([padding, df_hist], ignore_index=True)
        
        final_df = df_hist.tail(min_rows).reset_index(drop=True)
        final_df['Datetime'] = pd.to_datetime(final_df['Datetime'])
        return final_df

    except Exception as e:
        print(f"CSV_SYNC_ERROR|{e}")
        return pd.DataFrame()

def get_latest_data():
    return fetch_yf_data().tail(1)

# -------- TEST BLOCK (5 ROWS) --------
if __name__ == "__main__":
    print(f"=== Kotak Neo CSV Sync Test: {TICKER} ===")
    df = fetch_yf_data()
    if not df.empty:
        print("LAST 5 ROWS:")
        print(df.tail(5))
    else:
        print("Data fetch failed.")

