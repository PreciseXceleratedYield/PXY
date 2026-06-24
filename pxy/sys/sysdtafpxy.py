#sysdtafpxy.py
import warnings
import numpy as np
import pandas as pd
import yfinance as yf
from syscnfgpxy import TICKER, OHLC_MODE, TIMEZONE

# Silence future warning constraints completely
warnings.simplefilter(action='ignore', category=FutureWarning)

def get_shifted_heikin_ashi_ohlc(o, h, l, c):
    """
    Generates non-recursive candles matching our updated logic (Mode 0):
    - Close: Average of current OHLC (OHLC4)
    - Open: Average of previous OHLC (Previous OHLC4, falls back to raw open on index 0)
    - High/Low: Raw chart values
    """
    n = len(c)
    ha_o = np.zeros(n)
    ha_h = h.copy()
    ha_l = l.copy()
    
    # 1. Current Close is always the current OHLC4
    ha_c = (o + h + l + c) / 4.0
    
    # 2. Sequential calculation for the shifted Open value
    for i in range(n):
        if i == 0:
            ha_o[i] = o[i] # Fallback to raw open on the very first candle
        else:
            ha_o[i] = (o[i-1] + h[i-1] + l[i-1] + c[i-1]) / 4.0 # Previous candle's OHLC4
            
    return ha_o, ha_h, ha_l, ha_c

def apply_ohlc_transformation(df, mode=0):
    """Transforms raw arrays into the single distinct structural format"""
    if df.empty: 
        return df
        
    o = df['Open'].to_numpy()
    h = df['High'].to_numpy()
    l = df['Low'].to_numpy()
    c = df['Close'].to_numpy()
    
    if mode == 0:
        df['Open'], df['High'], df['Low'], df['Close'] = get_shifted_heikin_ashi_ohlc(o, h, l, c)
    else:
        print(f"SYSTEM_WARNING | Mode {mode} unrecognized. Defaulting to Mode 0 structure.")
        df['Open'], df['High'], df['Low'], df['Close'] = get_shifted_heikin_ashi_ohlc(o, h, l, c)
        
    return df

def fetch_yf_data(period=None, interval="1m", target_rows=60):
    """DYNAMIC HISTORICAL SLICE RETRIEVAL ENGINE WITH SIGNATURE BACKWARD-COMPATIBILITY"""
    ticker_obj = yf.Ticker(TICKER)
    df = pd.DataFrame()
    
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
                    if len(df) >= target_rows:
                        break
            except Exception:
                pass

    if df.empty or len(df) < target_rows:
        print(f"CRITICAL: Failed to collect minimum {target_rows} candles from history profiles.")
        return pd.DataFrame()
        
    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index)
        
    if df.index.tz is None:
        df = df.tz_localize('UTC').tz_convert(TIMEZONE)
    else:
        df = df.tz_convert(TIMEZONE)
        
    df = df.tail(target_rows).copy()
    
    processed_df = apply_ohlc_transformation(df, mode=OHLC_MODE)
    return processed_df
