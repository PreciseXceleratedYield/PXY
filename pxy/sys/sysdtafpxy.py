import warnings 
import numpy as np 
import pandas as pd 
import yfinance as yf 
from syscnfgpxy import TICKER, TIMEZONE  # Removed OHLC_MODE import since it is hardcoded now

warnings.simplefilter(action='ignore', category=FutureWarning)

def apply_ohlc_transformation(df):
    """Applies Mode 0: Custom candle transformation logic matching Pine Script."""
    if df.empty:
        return df
        
    # Step 1: Detect raw candle color based on standard close/open
    is_green = df['Close'] >= df['Open']
    
    # Step 2: Dynamically calculate Custom Close based on candle color
    df['Close'] = np.where(is_green, (df['Close'] + df['High']) / 2, (df['Close'] + df['Low']) / 2)
    
    # Step 3: Recalculate Custom Open, High, and Low boundaries
    df['Open'] = (df['High'] + df['Low'] + df['Close']) / 3
    df['High'] = df[['High', 'Open', 'Close']].max(axis=1)
    df['Low'] = df[['Low', 'Open', 'Close']].min(axis=1)
    
    return df

def fetch_yf_data(period=None, interval="1m", target_rows=60):
    """DYNAMIC HISTORICAL SLICE RETRIEVAL ENGINE FOR DATA"""
    ticker_obj = yf.Ticker(TICKER)
    df = pd.DataFrame()
    
    # Warmup window to accommodate the 42 SMA calculation smoothly
    buffer_rows = target_rows + 45

    if period is not None:
        try:
            df = ticker_obj.history(period=period, interval=interval)
        except Exception as e:
            print(f"ERROR: Explicit download failed for period={period} | {e}")
            
    if df.empty:
        for search_period in ["5d", "7d", "max"]:
            try:
                df = ticker_obj.history(period=search_period, interval=interval)
                if not df.empty:
                    df.dropna(inplace=True)
                    if len(df) >= buffer_rows:
                        break
            except Exception:
                pass
                
    if df.empty or len(df) < buffer_rows:
        print(f"CRITICAL: Failed to collect minimum {buffer_rows} candles.")
        return pd.DataFrame()
        
    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index)
        
    if df.index.tz is None:
        df = df.tz_localize('UTC').tz_convert(TIMEZONE)
    else:
        df = df.tz_convert(TIMEZONE)
        
    # Directly process using the mandatory transformed candle engine
    processed_df = apply_ohlc_transformation(df.copy())
    
    # Calculate 42 SMA directly on the transformed closing prices
    processed_df['SMA_42'] = processed_df['Close'].rolling(window=42).mean()
    
    return processed_df.tail(target_rows)

