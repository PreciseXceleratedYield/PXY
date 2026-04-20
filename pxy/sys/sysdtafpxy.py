import sys, os, warnings
import pandas as pd
from datetime import datetime
from syscnfgpxy import TICKER

# Silence the concat FutureWarning
warnings.simplefilter(action='ignore', category=FutureWarning)

# ---------------- PATH MANAGEMENT ----------------
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__)) 
RUN_DIR = os.path.join(CURRENT_DIR, "exe", "run")
if RUN_DIR not in sys.path: sys.path.append(RUN_DIR)

from runclntpxy import get_session

# --- CONFIGURATION ---
CSV_FILE = f"{TICKER.lower().replace(' ', '_')}_history.csv"
DEFAULT_MIN_ROWS = 50

def get_lot_size(t):
    """Current 2026 NSE lot sizes."""
    if t == "Nifty Bank": return 30
    if t == "Nifty 50": return 75
    return None

def fetch_yf_data(ticker=None, min_rows=DEFAULT_MIN_ROWS):
    t = ticker or TICKER
    now = datetime.now()
    today_str = now.strftime("%Y-%m-%d")
    current_min = now.strftime("%Y-%m-%d %H:%M:00")
    
    try:
        client = get_session()
        # Nifty 50 and Nifty Bank require exact string names in Kotak Neo V2
        instr_tokens = [{"instrument_token": t, "exchange_segment": "nse_cm"}]
        
        # Kotak API Call
        response = client.quotes(instrument_tokens=instr_tokens, quote_type="ltp")
        
        # --- FIX: Access first item in list ---
        if not isinstance(response, list) or len(response) == 0:
            return pd.DataFrame()
        
        # Access the first dictionary in the response list
        raw = response[0] 
        
        # Extract live price (Index Value or Last Traded Price)
        ltp = float(raw.get("last_traded_price", raw.get("ltp", raw.get("iv", 0))))
        if ltp == 0: return pd.DataFrame()
        
        # Load and clean history for today only
        if os.path.exists(CSV_FILE):
            df_hist = pd.read_csv(CSV_FILE)
            if 'LotSize' in df_hist.columns: df_hist.drop(columns=['LotSize'], inplace=True)
            df_hist['Datetime'] = pd.to_datetime(df_hist['Datetime'])
            df_hist = df_hist[df_hist['Datetime'].dt.strftime('%Y-%m-%d') == today_str]
        else:
            df_hist = pd.DataFrame(columns=["Datetime", "Open", "High", "Low", "Close", "Volume"])

        # --- REAL-TIME 1-MINUTE OHLC LOGIC ---
        live_dt = pd.to_datetime(current_min)
        if not df_hist.empty and df_hist['Datetime'].iloc[-1] == live_dt:
            # SAME MINUTE: Update High, Low, and Close
            idx = df_hist.index[-1]
            df_hist.at[idx, 'High'] = max(float(df_hist.at[idx, 'High']), ltp)
            df_hist.at[idx, 'Low'] = min(float(df_hist.at[idx, 'Low']), ltp)
            df_hist.at[idx, 'Close'] = ltp
        else:
            # NEW MINUTE: Start a fresh candle
            new_row = {"Datetime": current_min, "Open": ltp, "High": ltp, "Low": ltp, "Close": ltp, "Volume": 0}
            df_hist = pd.concat([df_hist, pd.DataFrame([new_row])], ignore_index=True)
        
        # Save CSV
        df_hist.to_csv(CSV_FILE, index=False)

        # Backfill for strategy stability
        if len(df_hist) < min_rows:
            padding = pd.DataFrame([df_hist.iloc[-1].to_dict()] * (min_rows - len(df_hist)))
            df_hist = pd.concat([padding, df_hist], ignore_index=True)
        
        return df_hist.tail(min_rows).reset_index(drop=True)

    except Exception as e:
        print(f"SYNC_ERROR: {e}")
        return pd.DataFrame()

if __name__ == "__main__":
    df = fetch_yf_data()
    if not df.empty:
        print(f"LIVE UPDATE | Price: {df['Close'].iloc[-1]} | Time: {df['Datetime'].iloc[-1]}")

