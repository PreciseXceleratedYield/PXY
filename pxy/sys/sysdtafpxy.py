import warnings
import numpy as np
import pandas as pd
import yfinance as yf
from syscnfgpxy import TICKER, OHLC_MODE

warnings.simplefilter(action='ignore', category=FutureWarning)

# Explicitly enforce Indian Standard Time zone mapping
TIMEZONE = 'Asia/Kolkata'

def apply_ohlc_transformation(df, mode=1):
    """
    Executes structural, isolated mathematical transformations based on explicit modes.
    No recursive loops are utilized.
    """
    if df.empty:
        return df
        
    out = df.copy()
    raw_o = df['Open'].to_numpy()
    raw_h = df['High'].to_numpy()
    raw_l = df['Low'].to_numpy()
    raw_c = df['Close'].to_numpy()
    
    # ⚡ Mode 0: Hyper-Sensitive Modified Close Candles
    # Green Close (Close >= Open) -> Transforms to High
    # Red Close (Close < Open) -> Transforms to Low
    if mode == 0:
        out['Close'] = np.where(raw_c >= raw_o, raw_h, raw_l)
        return out

    # Mode 1: Raw Candles
    elif mode == 1:
        return out
        
    # Mode 2: Mid-Body (Only Close changes to OC/2)
    elif mode == 2:
        out['Close'] = (raw_o + raw_c) / 2.0
        return out
        
    # Mode 3: Full Range (Only Close changes to OHLC/4)
    elif mode == 3:
        out['Close'] = (raw_o + raw_h + raw_l + raw_c) / 4.0
        return out
        
    # Mode 4: Average OHLC of Modes 1, 2, 3, and 4 (All columns transform)
    elif mode == 4:
        # Step 1: Pre-calculate the Close values for Modes 1, 2, and 3
        m1_c = raw_c
        m2_c = (raw_o + raw_c) / 2.0
        m3_c = (raw_o + raw_h + raw_l + raw_c) / 4.0
        
        # Step 2: Solve the algebraic circular equation for Mode 4's Close
        m4_c = (m1_c + m2_c + m3_c) / 3.0
        
        # Step 3: Solve the algebraic circular equations for Open, High, and Low
        out['Open'] = raw_o
        out['High'] = raw_h
        out['Low'] = raw_l
        out['Close'] = (m1_c + m2_c + m3_c + m4_c) / 4.0
        return out
        
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
        
    if df.index.tz is None:
        df = df.tz_localize('UTC').tz_convert(TIMEZONE)
    else:
        df = df.tz_convert(TIMEZONE)
        
    processed_df = apply_ohlc_transformation(df, mode=OHLC_MODE)
    return processed_df.tail(target_rows)


