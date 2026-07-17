# sysdtafpxy.py
import warnings
import numpy as np
import pandas as pd
import yfinance as yf
from syscnfgpxy import TICKER

warnings.simplefilter(action='ignore', category=FutureWarning)

# Explicitly enforce Indian Standard Time zone mapping
TIMEZONE = 'Asia/Kolkata'

def apply_ohlc_transformation(df, mode=1):
    """
    Returns pure, unaltered raw candles exclusively.
    All synthetic transformations have been stripped out.
    """
    return df.copy()

def fetch_yf_data(period=None, interval="1m", target_rows=60):
    """Dynamic historical ingestion engine utilizing clean raw data"""
    ticker_obj = yf.Ticker(TICKER)
    df = pd.DataFrame()
    buffer_rows = target_rows + 5
    
    if period is not None:
        try:
            df = ticker_obj.history(period=period, interval=interval)
        except Exception:
            pass
            
    if df.empty:
        for search_period in ["5d", "7d", "max"]:
            try:
                df = ticker_obj.history(period=search_period, interval=interval)
                if not df.empty:
                    df.dropna(subset=['Open', 'High', 'Low', 'Close'], inplace=True)
                    if len(df) >= buffer_rows:
                        break
            except Exception:
                pass
                
    if df.empty or len(df) < buffer_rows:
        return pd.DataFrame()
        
    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index)
        
    # Enforces absolute conversion to Indian Standard Time (IST)
    if df.index.tz is None:
        df = df.tz_localize('UTC').tz_convert(TIMEZONE)
    else:
        df = df.tz_convert(TIMEZONE)
        
    # Process pure raw candles
    processed_df = apply_ohlc_transformation(df, mode=1)
    
    # Generate the color state series directly using raw Close vs raw Open
    is_green = processed_df['Close'] >= processed_df['Open']
    processed_df["pxy_color"] = np.select([is_green], ["green"], default="red")
    
    return processed_df.tail(target_rows)

