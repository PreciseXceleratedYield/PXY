import warnings
import numpy as np
import pandas as pd
import yfinance as yf
from syscnfgpxy import TICKER

warnings.simplefilter(action='ignore', category=FutureWarning)

# Explicitly enforce Indian Standard Time zone mapping
TIMEZONE = 'Asia/Kolkata'

import numpy as np

def apply_ohlc_transformation(df, mode=1):
    """Executes structural, isolated mathematical transformations based on explicit modes."""
    if df.empty:
        return df

    out = df.copy()
    raw_o = df['Open'].to_numpy()
    raw_h = df['High'].to_numpy()
    raw_l = df['Low'].to_numpy()
    raw_c = df['Close'].to_numpy()

    # ⚡ Mode 0: Hyper-Sensitive Modified Close Candles (Triggered if market is SIDE)
    if mode == 0:
        # Override the Open price to match the actual raw Close
        out['Open'] = raw_c
        # Calculate the custom close transformation matrix
        out['Close'] = np.where(raw_c >= raw_o, (raw_c + raw_h) / 2.0, (raw_c + raw_l) / 2.0)
        return out

    # ⚡ Mode 1: Raw Candles
    elif mode == 1:
        return out

    # ⚡ Mode 2: OC/2 (Triggered if market is BULL or BEAR)
    elif mode == 2:
        out['Close'] = (raw_o + raw_c) / 2.0
        return out

    # ⚡ Mode 3: OCC/3
    elif mode == 3:
        out['Close'] = (raw_o + (2 * raw_c)) / 3.0
        return out

    # ⚡ Mode 4: OCCC/4
    elif mode == 4:
        out['Close'] = (raw_o + (3 * raw_c)) / 4.0
        return out

    # ⚡ Mode 5: OHLCC/5
    elif mode == 5:
        out['Close'] = (raw_o + raw_h + raw_l + (2 * raw_c)) / 5.0
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
        
    # ==========================================================================
    # ⚡ LOCAL IMPORT SHIELD: Prevents Circular Dependency Faults
    # ==========================================================================
    from sysstrndpxy import get_market_trend
    
    # Step 1: Run raw data through classifier to detect current market structure
    market_state = get_market_trend(df)
    
    # Step 2: Assign logic mode dynamically based on state output (0 for SIDE, else 1)
    dynamic_mode = 0 if market_state == 'SIDE' else 0
    
    # Step 3: Transform close values using the runtime calculated mode switch
    processed_df = apply_ohlc_transformation(df, mode=dynamic_mode)
    return processed_df.tail(target_rows)

