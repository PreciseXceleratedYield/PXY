import sys, os, warnings
import pandas as pd
from datetime import datetime
from syscnfgpxy import TICKER

warnings.simplefilter(action='ignore', category=FutureWarning)

# ---------------- PATH MANAGEMENT ----------------
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__)) 
RUN_DIR = os.path.join(CURRENT_DIR, "exe", "run")
if RUN_DIR not in sys.path: sys.path.append(RUN_DIR)

from runclntpxy import get_session

# --- CONFIGURATION ---
CSV_FILE = f"{TICKER.lower().replace(' ', '_')}_history.csv"
DEFAULT_MIN_ROWS = 50

def fetch_yf_data(ticker=None, min_rows=DEFAULT_MIN_ROWS):
    t = ticker or TICKER
    now = datetime.now()
    today_str = now.strftime("%Y-%m-%d")
    current_min = now.strftime("%Y-%m-%d %H:%M:00")
    
    try:
        # --- 1. FETCH LIVE QUOTE ---
        client = get_session()
        instr_tokens = [{"instrument_token": t, "exchange_segment": "nse_cm"}]
        response = client.quotes(instrument_tokens=instr_tokens, quote_type="ltp")
        
        if not isinstance(response, list) or len(response) == 0:
            return pd.DataFrame()

        raw = response 
        # Extract live price (Index Value or Last Traded Price)
        ltp = float(raw.get("last_traded_price", raw.get("ltp", raw.get("iv", 0))))
        if ltp == 0: return pd.DataFrame()
        
        # --- 2. LOAD & CLEAN TODAY'S HISTORY ---
        if os.path.exists(CSV_FILE):
            df_hist = pd.read_csv(CSV_FILE)
            df_hist['Datetime'] = pd.to_datetime(df_hist['Datetime'])
            # Filter today's data only
            df_hist = df_hist[df_hist['Datetime'].dt.strftime('%Y-%m-%d') == today_str]
        else:
            df_hist = pd.DataFrame(columns=["Datetime", "Open", "High", "Low", "Close", "Volume"])

        # --- 3. CONSTRUCT OHLC (CLOSE PREVIOUS & BUILD CURRENT) ---
        live_dt = pd.to_datetime(current_min)
        
        if not df_hist.empty and df_hist['Datetime'].iloc[-1] == live_dt:
            # CURRENT MINUTE STILL OPEN: Update High, Low, and Close dynamically
            idx = df_hist.index[-1]
            df_hist.at[idx, 'High'] = max(float(df_hist.at[idx, 'High']), ltp)
            df_hist.at[idx, 'Low'] = min(float(df_hist.at[idx, 'Low']), ltp)
            df_hist.at[idx, 'Close'] = ltp
        else:
            # PREVIOUS MINUTE CLOSED: The last row in df_hist is now final.
            # START NEW MINUTE: Fresh candle begins with LTP as base.
            new_row = {
                "Datetime": current_min,
                "Open": ltp,
                "High": ltp,
                "Low": ltp,
                "Close": ltp,
                "Volume": 0
            }
            df_hist = pd.concat([df_hist, pd.DataFrame([new_row])], ignore_index=True)
        
        # --- 4. SAVE CLEAN CSV ---
        df_hist.to_csv(CSV_FILE, index=False)

        # --- 5. BACKFILL TO 50 ROWS FOR DOWNSTREAM ---
        if len(df_hist) < min_rows:
            # Pad with current candle to prevent strategy crash
            fill_val = df_hist.iloc[-1].to_dict()
            padding = pd.DataFrame([fill_val] * (min_rows - len(df_hist)))
            df_hist = pd.concat([padding, df_hist], ignore_index=True)
        
        # Ensure correct column order and return last 50 rows
        final_df = df_hist.tail(min_rows).reset_index(drop=True)
        final_df['Datetime'] = pd.to_datetime(final_df['Datetime'])
        return final_df

    except Exception as e:
        print(f"SYNC_ERROR: {e}")
        return pd.DataFrame()

def get_latest_data():
    """Returns the absolute latest live OHLC row"""
    return fetch_yf_data().tail(1)

if __name__ == "__main__":
    df = fetch_yf_data()
    if not df.empty:
        # Display the 5 newest constructed rows
        print("CONSTRUCTED 1-MIN OHLC (Today Only):")
        print(df.tail(5))

