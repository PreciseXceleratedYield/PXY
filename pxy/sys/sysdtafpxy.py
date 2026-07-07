import warnings
import numpy as np
import pandas as pd
import yfinance as yf
from syscnfgpxy import TICKER, TIMEZONE

warnings.simplefilter(action='ignore', category=FutureWarning)

def apply_ohlc_transformation(df):
    """Transforms standard candles into Heikin-Ashi candles without changing column names."""
    if df.empty:
        return df
        
    ha_df = df.copy()
    
    # 1. Calculate HA Close
    ha_close = (df['Open'] + df['High'] + df['Low'] + df['Close']) / 4
    
    # 2. Calculate HA Open iteratively
    ha_open = np.zeros(len(df))
    ha_open[0] = (df['Open'].iloc[0] + df['Close'].iloc[0]) / 2
    
    for i in range(1, len(df)):
        ha_open[i] = (ha_open[i-1] + ha_close.iloc[i-1]) / 2
        
    # 3. Calculate HA High and HA Low
    ha_high = np.maximum.reduce([df['High'].values, ha_open, ha_close.values])
    ha_low = np.minimum.reduce([df['Low'].values, ha_open, ha_close.values])
    
    # Overwrite the standard columns so downstream logic reads HA data natively
    ha_df['Open'] = ha_open
    ha_df['High'] = ha_high
    ha_df['Low'] = ha_low
    ha_df['Close'] = ha_close
    
    return ha_df

def fetch_yf_data(period=None, interval="1m", target_rows=60):
    """DYNAMIC HISTORICAL SLICE RETRIEVAL ENGINE FOR DATA"""
    ticker_obj = yf.Ticker(TICKER)
    df = pd.DataFrame()
    
    # Warmup window to accommodate the 42 SMA and HA initialization smoothly
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
        
    # Process using the Heikin-Ashi candle engine
    processed_df = apply_ohlc_transformation(df.copy())
    
    # Calculate 42 SMA on the newly transformed Heikin-Ashi closing prices
    processed_df['SMA_42'] = processed_df['Close'].rolling(window=42).mean()
    
    return processed_df.tail(target_rows)

