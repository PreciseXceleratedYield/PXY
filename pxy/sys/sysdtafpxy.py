import warnings 
import pandas as pd 
import yfinance as yf
from syscnfgpxy import TICKER 

warnings.simplefilter(action='ignore', category=FutureWarning) 

# --- CONFIGURATION --- 
DEFAULT_INTERVAL = "1m" 
TARGET_TOTAL_ROWS = 42 

def fetch_yf_data(period="5d", interval=None, min_rows=None, ticker=None): 
    """ 
    YFINANCE PADDED OHLC ENGINE
    Guarantees exactly 42 rows by pooling today and yesterday's data.
    """ 
    target_interval = interval or DEFAULT_INTERVAL 
    target_rows = min_rows or TARGET_TOTAL_ROWS 
    ticker_symbol = ticker or TICKER 
    
    try:
        ticker_obj = yf.Ticker(ticker_symbol) 
        
        # Always download 5 days to ensure we have a robust historical backlog for padding
        df = ticker_obj.history(period="5d", interval=target_interval) 
        
        if df.empty:
            print("WARNING: Data engine returned an empty DataFrame.")
            return pd.DataFrame()
            
        df.dropna(inplace=True) 
        
        # DatetimeIndex alignment fix to prevent conversion parsing crashes downstream
        if not isinstance(df.index, pd.DatetimeIndex):
            df.index = pd.to_datetime(df.index)
            
        # Select the absolute last 42 bars from the 5-day dataset pool
        # This naturally merges today's morning bars with yesterday's market close
        return df.tail(target_rows) 
        
    except Exception as e:
        print(f"YFINANCE_DATA_ERROR | {e}")
        return pd.DataFrame()

def get_latest_data(): 
    """Returns the most recent single row from the engine"""
    return fetch_yf_data().tail(1) 

if __name__ == "__main__": 
    print(f"=== Pure YFinance Data Sync Engine | {TICKER} ===") 
    df = fetch_yf_data() 
    if not df.empty: 
        print(f"Total Rows Retrieved: {len(df)} (Target: {TARGET_TOTAL_ROWS})")
        print(df.tail(5))

