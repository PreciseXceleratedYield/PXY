import warnings 
import numpy as np 
import pandas as pd 
import yfinance as yf 
from syscnfgpxy import TICKER, TIMEZONE  # Removed OHLC_MODE import since it is hardcoded now

warnings.simplefilter(action='ignore', category=FutureWarning)

def apply_ohlc_transformation(df):
    """Applies normal, unaltered candle structure directly from the raw data feed."""
    # Keeps normal candles as requested; returning unmodified data frames
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
        
    # Directly process using the normal candle bypass engine
    processed_df = apply_ohlc_transformation(df.copy())
    
    # Calculate 42 SMA directly on the normal closing prices
    processed_df['SMA_42'] = processed_df['Close'].rolling(window=42).mean()
    
    return processed_df.tail(target_rows)

