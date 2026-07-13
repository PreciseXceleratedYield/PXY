
import warnings
import numpy as np
import pandas as pd
import yfinance as yf
from syscnfgpxy import TICKER, OHLC_MODE

warnings.simplefilter(action='ignore', category=FutureWarning)

# Explicitly enforce Indian Standard Time zone mapping
TIMEZONE = 'Asia/Kolkata'

def _get_ha_values(df):
    """Calculates structurally accurate Heikin-Ashi arrays using independent memory allocations"""
    raw_open = df['Open'].to_numpy(copy=True)
    raw_high = df['High'].to_numpy(copy=True)
    raw_low = df['Low'].to_numpy(copy=True)
    raw_close = df['Close'].to_numpy(copy=True)
    
    ha_close = (raw_open + raw_high + raw_low + raw_close) / 4.0
    ha_open = np.empty_like(raw_open)
    ha_open[0] = raw_open[0]  # Secure initialization assignment
    
    # Secure recursive open generation without memory leaks
    for i in range(1, len(raw_open)):
        ha_open[i] = (ha_open[i-1] + ha_close[i-1]) / 2.0
        
    ha_high = np.maximum(raw_high, np.maximum(ha_open, ha_close))
    ha_low = np.minimum(raw_low, np.minimum(ha_open, ha_close))
    
    return (
        pd.Series(ha_open, index=df.index),
        pd.Series(ha_high, index=df.index),
        pd.Series(ha_low, index=df.index),
        pd.Series(ha_close, index=df.index)
    )

def apply_ohlc_transformation(df, mode=1):
    """
    Executes exactly 6 structural, isolated OHLC mathematical transformations:
    Mode 0: Hyper-Sensitive Modified Candles (Pine Script Port)
    Mode 1: Raw Candles
    Mode 2: Mid-Body (OC/2) Pure Math Candles
    Mode 3: Full Range (OHLC/4) Pure Math Candles
    Mode 4: Standard Heikin-Ashi Candles
    Mode 5: Master Ensemble Average of Modes 0, 1, 2, 3, and 4 (Divided by 5)
    """
    if df.empty:
        return df
        
    out = df.copy()
    raw_o = df['Open'].copy()
    raw_h = df['High'].copy()
    raw_l = df['Low'].copy()
    raw_c = df['Close'].copy()
    
    if mode == 0:
        out['High'] = np.where(raw_c >= raw_o, raw_c, raw_h)
        out['Low'] = np.where(raw_c < raw_o, raw_c, raw_l)
        return out

    elif mode == 1:
        return out
        
    elif mode == 2:
        out['Close'] = (raw_o + raw_c) / 2.0
        
    elif mode == 3:
        out['Close'] = (raw_o + raw_h + raw_l + raw_c) / 4.0
        
    elif mode == 4:
        ha_o, ha_h, ha_l, ha_c = _get_ha_values(df)
        out['Open'], out['High'], out['Low'], out['Close'] = ha_o, ha_h, ha_l, ha_c
        
    elif mode == 5:
        # Component 0: Mode 0 implementation
        m0_o = raw_o
        m0_h = np.where(raw_c >= raw_o, raw_c, raw_h)
        m0_l = np.where(raw_c < raw_o, raw_c, raw_l)
        m0_c = raw_c

        # Component 1: Mode 1 implementation
        m1_o, m1_h, m1_l, m1_c = raw_o, raw_h, raw_l, raw_c

        # Component 2: Mode 2 implementation
        m2_o, m2_h, m2_l, m2_c = raw_o, raw_h, raw_l, (raw_o + raw_c) / 2.0

        # Component 3: Mode 3 implementation
        m3_o, m3_h, m3_l, m3_c = raw_o, raw_h, raw_l, (raw_o + raw_h + raw_l + raw_c) / 4.0

        # Component 4: Mode 4 implementation
        m4_o, m4_h, m4_l, m4_c = _get_ha_values(df)
        
        # Comprehensive 5-Way Master Ensemble Math Matrix
        out['Open'] = (m0_o + m1_o + m2_o + m3_o + m4_o) / 5.0
        out['High'] = (m0_h + m1_h + m2_h + m3_h + m4_h) / 5.0
        out['Low'] = (m0_l + m1_l + m2_l + m3_l + m4_l) / 5.0
        out['Close'] = (m0_c + m1_c + m2_c + m3_c + m4_c) / 5.0
        
    return out

def fetch_yf_data(period=None, interval="1m", target_rows=60):
    """Dynamic historical ingestion engine utilizing vectorized structural transformations"""
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
        
    processed_df = apply_ohlc_transformation(df, mode=OHLC_MODE)
    return processed_df.tail(target_rows)

