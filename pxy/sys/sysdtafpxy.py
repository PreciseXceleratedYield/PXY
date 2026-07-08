import warnings 
import numpy as np 
import pandas as pd 
import yfinance as yf 
from syscnfgpxy import TICKER, OHLC_MODE, TIMEZONE 

warnings.simplefilter(action='ignore', category=FutureWarning)

def apply_ohlc_transformation(df, mode=1):
    """Applies the selected geometric or recursive candle transformation matrix."""
    if df.empty:
        return df
        
    df_out = df.copy()
    
    # Pre-calculate component datasets for clean matrix blending in Mode 4
    # MODE 0 Arrays
    m0_vals = df['Close'].values
    
    # MODE 1 Arrays (Raw)
    m1_open  = df['Open'].values
    m1_high  = df['High'].values
    m1_low   = df['Low'].values
    m1_close = df['Close'].values
    
    # MODE 2 Arrays (Recursive HA)
    m2_close = (m1_open + m1_high + m1_low + m1_close) / 4.0
    m2_open = np.zeros(len(df))
    m2_open[0] = (m1_open[0] + m1_close[0]) / 2.0
    for i in range(1, len(df)):
        m2_open[i] = (m2_open[i-1] + m2_close[i-1]) / 2.0
    m2_high = np.maximum(m1_high, np.maximum(m2_open, m2_close))
    m2_low  = np.minimum(m1_low, np.minimum(m2_open, m2_close))
    
    # MODE 3 Arrays
    m3_vals = ((df['Open'] + df['Close']) / 2.0).values

    # MODE RUNTIME ROUTER
    if mode == 0:
        df_out['Open']  = m0_vals
        df_out['High']  = m0_vals
        df_out['Low']   = m0_vals
        df_out['Close'] = m0_vals
        return df_out

    elif mode == 1:
        return df_out
        
    elif mode == 2:
        df_out['Open']  = m2_open
        df_out['High']  = m2_high
        df_out['Low']   = m2_low
        df_out['Close'] = m2_close
        return df_out

    elif mode == 3:
        df_out['Open']  = m3_vals
        df_out['High']  = m3_vals
        df_out['Low']   = m3_vals
        df_out['Close'] = m3_vals
        return df_out

    # MODE 4: Blended Matrix (Mean Average of Mode 0, 1, 2, and 3)
    elif mode == 4:
        df_out['Open']  = (m0_vals + m1_open  + m2_open  + m3_vals) / 4.0
        df_out['High']  = (m0_vals + m1_high  + m2_high  + m3_vals) / 4.0
        df_out['Low']   = (m0_vals + m1_low   + m2_low   + m3_vals) / 4.0
        df_out['Close'] = (m0_vals + m1_close + m2_close + m3_vals) / 4.0
        return df_out
        
    else:
        print(f"SYSTEM_WARNING | Mode {mode} unrecognized. Defaulting to Mode 1 Raw Candles.")
        return df_out

def fetch_yf_data(period=None, interval="1m", target_rows=60):
    """DYNAMIC HISTORICAL SLICE RETRIEVAL ENGINE FOR DATA RECOVERY"""
    ticker_obj = yf.Ticker(TICKER)
    df = pd.DataFrame()
    
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
        
    processed_df = apply_ohlc_transformation(df.copy(), mode=OHLC_MODE)
    
    # Calculate 42 SMA directly on the transformed closing prices
    processed_df['SMA_42'] = processed_df['Close'].rolling(window=42).mean()
    
    return processed_df.tail(target_rows)


