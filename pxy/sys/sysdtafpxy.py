import sys, os, warnings 
import pandas as pd 
from datetime import datetime 
from syscnfgpxy import TICKER 

warnings.simplefilter(action='ignore', category=FutureWarning) 

# ---------------- GLOBAL SWITCH ---------------- 
SOURCE = "YF" # "NEO" or "YF" 

# ---------------- PATH MANAGEMENT (NEO ONLY) ---------------- 
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__)) 
RUN_DIR = os.path.join(CURRENT_DIR, "exe", "run") 
if RUN_DIR not in sys.path: 
    sys.path.append(RUN_DIR) 
from runclntpxy import get_session 

CSV_FILE = f"{TICKER.lower().replace(' ', '_')}_history.csv" 
DEFAULT_MIN_ROWS = 50 

def _fetch_neo_data(period="1d", interval="1m", min_rows=None, ticker=None): 
    """ KOTAK NEO REAL-TIME OHLC ENGINE """ 
    t = ticker or TICKER 
    target_rows = min_rows or DEFAULT_MIN_ROWS 
    now = datetime.now() 
    today_str = now.strftime("%Y-%m-%d") 
    current_min = now.strftime("%Y-%m-%d %H:%M:00") 
    try: 
        client = get_session() 
        instr_tokens = [{"instrument_token": t, "exchange_segment": "nse_cm"}] 
        response = client.quotes(instrument_tokens=instr_tokens, quote_type="ltp") 
        if isinstance(response, list) and len(response) > 0: 
            raw = response[0] 
        else: 
            raw = {} 
        ltp = float(raw.get("last_traded_price", raw.get("ltp", raw.get("iv", 0)))) 
        if ltp > 0: 
            if os.path.exists(CSV_FILE): 
                df_hist = pd.read_csv(CSV_FILE) 
                df_hist['Datetime'] = pd.to_datetime(df_hist['Datetime']) 
                df_hist = df_hist[df_hist['Datetime'].dt.strftime('%Y-%m-%d') == today_str] 
            else: 
                df_hist = pd.DataFrame(columns=["Datetime", "Open", "High", "Low", "Close", "Volume"]) 
            live_dt = pd.to_datetime(current_min) 
            if not df_hist.empty and df_hist['Datetime'].iloc[-1] == live_dt: 
                idx = df_hist.index[-1] 
                df_hist.at[idx, 'High'] = max(float(df_hist.at[idx, 'High']), ltp) 
                df_hist.at[idx, 'Low'] = min(float(df_hist.at[idx, 'Low']), ltp) 
                df_hist.at[idx, 'Close'] = ltp 
            else: 
                new_row = { 
                    "Datetime": current_min, "Open": ltp, "High": ltp, "Low": ltp, "Close": ltp, "Volume": 0 
                } 
                df_hist = pd.concat([df_hist, pd.DataFrame([new_row])], ignore_index=True) 
            df_hist.to_csv(CSV_FILE, index=False) 
        if os.path.exists(CSV_FILE): 
            df = pd.read_csv(CSV_FILE) 
            df['Datetime'] = pd.to_datetime(df['Datetime']) 
            if len(df) < target_rows: 
                last_row = df.iloc[-1].to_dict() if not df.empty else { 
                    "Datetime": current_min, "Open": ltp, "High": ltp, "Low": ltp, "Close": ltp, "Volume": 0 
                } 
                padding = pd.DataFrame([last_row] * (target_rows - len(df))) 
                df = pd.concat([padding, df], ignore_index=True) 
            return df.tail(target_rows).reset_index(drop=True) 
        return pd.DataFrame() 
    except Exception as e: 
        print(f"NEO_DATA_ERROR|{e}") 
        return pd.DataFrame() 

import yfinance as yf 
DEFAULT_INTERVAL = "1m" 
DEFAULT_MIN_ROWS_YF = 5 

def _fetch_yf_data(period="5d", interval=None, min_rows=None, ticker=None): 
    """ YFINANCE HISTORICAL DATA ENGINE """ 
    interval = interval or DEFAULT_INTERVAL 
    min_rows = min_rows or DEFAULT_MIN_ROWS_YF 
    ticker_symbol = ticker or TICKER 
    ticker_obj = yf.Ticker(ticker_symbol) 
    df = ticker_obj.history(period="5d", interval=interval) 
    df.dropna(inplace=True) 
    return df.tail(min_rows) 

def fetch_yf_data(period="1d", interval="1m", min_rows=None, ticker=None): 
    """ UNIFIED DATA INTERFACE """ 
    if SOURCE.upper() == "NEO": 
        return _fetch_neo_data(period=period, interval=interval, min_rows=min_rows, ticker=ticker) 
    else: 
        return _fetch_yf_data(period=period, interval=interval, min_rows=min_rows, ticker=ticker) 

def get_latest_data(): 
    return fetch_yf_data().tail(1) 

if __name__ == "__main__": 
    print(f"=== Data Sync Engine ({SOURCE}) | {TICKER} ===") 
    df = fetch_yf_data() 
    if not df.empty: 
        print(df.tail(5))

