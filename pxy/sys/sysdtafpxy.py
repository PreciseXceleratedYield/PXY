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

CSV_FILE = f"{TICKER.lower().replace(' ', '_')}_history.csv"
DEFAULT_MIN_ROWS = 50

def fetch_yf_data(ticker=None, min_rows=DEFAULT_MIN_ROWS):
    t = ticker or TICKER
    now = datetime.now()
    current_min = now.strftime("%Y-%m-%d %H:%M:00")
    
    try:
        client = get_session()
        # Nifty 50 requires exact string name as token
        instr_tokens = [{"instrument_token": t, "exchange_segment": "nse_cm"}]
        
        # Use quote_type="ltp" for faster live price retrieval
        response = client.quotes(instrument_tokens=instr_tokens, quote_type="ltp")
        
        if not isinstance(response, list) or len(response) == 0:
            return pd.DataFrame()

        # Kotak Neo often nests index values in 'iv' or 'ltp'
        raw = response[0]
        ltp = float(raw.get("last_traded_price", raw.get("ltp", raw.get("iv", 0))))

        if ltp == 0: return pd.DataFrame()
        
        # Load/Clean Today's History
        if os.path.exists(CSV_FILE):
            df_hist = pd.read_csv(CSV_FILE)
            df_hist['Datetime'] = pd.to_datetime(df_hist['Datetime'])
            df_hist = df_hist[df_hist['Datetime'].dt.date == now.date()]
        else:
            df_hist = pd.DataFrame(columns=["Datetime", "Open", "High", "Low", "Close", "Volume"])

        # Update 1-Minute OHLC
        live_dt = pd.to_datetime(current_min)
        if not df_hist.empty and df_hist['Datetime'].iloc[-1] == live_dt:
            idx = df_hist.index[-1]
            df_hist.at[idx, 'High'] = max(float(df_hist.at[idx, 'High']), ltp)
            df_hist.at[idx, 'Low'] = min(float(df_hist.at[idx, 'Low']), ltp)
            df_hist.at[idx, 'Close'] = ltp
        else:
            new_row = {"Datetime": current_min, "Open": ltp, "High": ltp, "Low": ltp, "Close": ltp, "Volume": 0}
            df_hist = pd.concat([df_hist, pd.DataFrame([new_row])], ignore_index=True)
        
        df_hist.to_csv(CSV_FILE, index=False)

        # Backfill for downstream stability
        if len(df_hist) < min_rows:
            padding = pd.DataFrame([df_hist.iloc[-1].to_dict()] * (min_rows - len(df_hist)))
            df_hist = pd.concat([padding, df_hist], ignore_index=True)
        
        return df_hist.tail(min_rows).reset_index(drop=True)

    except Exception as e:
        print(f"LTP_ERROR: {e}")
        return pd.DataFrame()

if __name__ == "__main__":
    df = fetch_yf_data()
    if not df.empty:
        # Success print
        print(f"LIVE UPDATE | Price: {df['Close'].iloc[-1]} | Time: {df['Datetime'].iloc[-1]}")

