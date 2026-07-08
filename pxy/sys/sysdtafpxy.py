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
    
    # MODE 1: Raw Baseline (Unaltered)
    if mode == 1:
        return df_out
        
    # MODE 2: Simplified Heikin-Ashi (Non-Recursive)
    elif mode == 2:
        close_vals = (df['Open'] + df['High'] + df['Low'] + df['Close']) / 4.0
        open_vals = (df['Open'] + df['Close']) / 2.0
        df_out['Close'] = close_vals
        df_out['Open'] = open_vals
        # High / Low are kept completely at raw chart levels per specification
        return df_out

    # MODE 7: Recursive OHLC/4 Candle Framework (Standard Heikin-Ashi)
    elif mode == 7:
        ha_close = (df['Open'] + df['High'] + df['Low'] + df['Close']) / 4.0
        ha_open = np.zeros(len(df))
        
        # Initialize the first row
        ha_open[0] = (df['Open'].iloc[0] + df['Close'].iloc[0]) / 2.0
        
        # Recursive calculation loop for open values
        for i in range(1, len(df)):
            ha_open[i] = (ha_open[i-1] + ha_close.iloc[i-1]) / 2.0
            
        df_out['Close'] = ha_close
        df_out['Open'] = ha_open
        df_out['High'] = np.maximum(df['High'].values, np.maximum(ha_open, ha_close))
        df_out['Low'] = np.minimum(df['Low'].values, np.minimum(ha_open, ha_close))
        return df_out
        
    # Fallback for other modes
    else:
        print(f"SYSTEM_WARNING | Mode {mode} unimplemented/unrecognized. Defaulting to Mode 1 Raw Candles.")
        return df_out

def fetch_yf_data(period=None, interval="1m", target_rows=60):
    """DYNAMIC HISTORICAL SLICE RETRIEVAL ENGINE FOR RAW MODE 1 DATA"""
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
        
    processed_df = apply_ohlc_transformation(df.copy(), mode=OHLC_MODE)
    
    # Calculate 42 SMA directly on the transformed closing prices
    processed_df['SMA_42'] = processed_df['Close'].rolling(window=42).mean()
    
    return processed_df.tail(target_rows)

