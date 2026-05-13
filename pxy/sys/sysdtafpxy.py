# sysdtafpxy.py
import warnings 
import pandas as pd 
import yfinance as yf
from syscnfgpxy import TICKER 

# Silence future warning constraints completely
warnings.simplefilter(action='ignore', category=FutureWarning) 

def fetch_yf_data(period="5d", interval="1m", min_rows=None, ticker=None): 
    """ 
    UNSLICED CONTINUOUS YFINANCE ENGINE
    Downloads multi-day context vectors to give SMA and ATR full mature lookback.
    Matches your TradingView Pine Script chart dataset availability.
    """ 
    ticker_symbol = ticker or TICKER 
    try:
        ticker_obj = yf.Ticker(ticker_symbol) 
        
        # Pull 5 days of history to provide deep lookup capabilities
        df = ticker_obj.history(period=period, interval=interval) 
        
        if df.empty:
            print("WARNING: Yahoo Finance data engine returned an empty frame.")
            return pd.DataFrame()
            
        df.dropna(inplace=True) 
        
        # Ensure index is an explicit DatetimeIndex for safe timezone calculations
        if not isinstance(df.index, pd.DatetimeIndex):
            df.index = pd.to_datetime(df.index)
            
        return df 
        
    except Exception as e:
        print(f"YFINANCE_DATA_ERROR | {e}")
        return pd.DataFrame()

def get_latest_data(): 
    """Returns the most recent live completed bar matrix row"""
    return fetch_yf_data().tail(1) 

if __name__ == "__main__": 
    print(f"=== Continuous YFinance Engine | Active Ticker: {TICKER} ===") 
    df = fetch_yf_data() 
    if not df.empty: 
        print(f"SUCCESS: Total Continuous Vector Rows Loaded: {len(df)}")

