import warnings
import numpy as np
import pandas as pd
import yfinance as yf
from syscnfgpxy import TICKER, OHLC_MODE, TIMEZONE

# Silence future warning constraints completely
warnings.simplefilter(action='ignore', category=FutureWarning)

def get_oc2_ohlc_mode1(o, h, l, c):
    """
    Generates alternative structural candles (Mode 1):
    - Close: (Current Open + Current Close) / 2.0 [OC2]
    - Open: (Previous Open + Previous Close) / 2.0 [Previous OC2]
    - High/Low: Raw chart values pass through directly
    """
    n = len(c)
    ha_o = np.zeros(n)
    ha_h = h.copy()
    ha_l = l.copy()
    
    # 1. Close is always the current bar's raw OC2
    ha_c = (o + c) / 2.0
    
    # 2. Open is always the previous bar's raw OC2
    for i in range(n):
        if i == 0:
            ha_o[i] = o[i]  # Fallback to raw open on the first array row
        else:
            ha_o[i] = (o[i-1] + c[i-1]) / 2.0
            
    return ha_o, ha_h, ha_l, ha_c

def apply_ohlc_transformation(df, mode=1):
    """Transforms raw arrays into the single distinct structural format"""
    if df.empty:
        return df
        
    o = df['Open'].to_numpy()
    h = df['High'].to_numpy()
    l = df['Low'].to_numpy()
    c = df['Close'].to_numpy()
    
    if mode == 1:
        df['Open'], df['High'], df['Low'], df['Close'] = get_oc2_ohlc_mode1(o, h, l, c)
    else:
        print(f"SYSTEM_WARNING | Mode {mode} unrecognized. Defaulting to Mode 1 OC/2 structure.")
        df['Open'], df['High'], df['Low'], df['Close'] = get_oc2_ohlc_mode1(o, h, l, c)
        
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
