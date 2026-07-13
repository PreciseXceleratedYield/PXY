import warnings 
import numpy as np 
import pandas as pd 
import yfinance as yf 
from syscnfgpxy import TICKER, OHLC_MODE, TIMEZONE 

warnings.simplefilter(action='ignore', category=FutureWarning)

def _get_ha_values(df):
    """Internal helper to calculate clean, standard Heikin-Ashi Series"""
    ha_close = (df['Open'] + df['High'] + df['Low'] + df['Close']) / 4
    
    ha_open = np.zeros(len(df))
    ha_open[0] = df['Open'].iloc[0]  # Validated row index initialization
    
    for i in range(1, len(df)):
        ha_open[i] = (ha_open[i-1] + ha_close.iloc[i-1]) / 2
        
    ha_high = np.maximum(df['High'].values, np.maximum(ha_open, ha_close.values))
    ha_low = np.minimum(df['Low'].values, np.minimum(ha_open, ha_close.values))
    
    return (pd.Series(ha_open, index=df.index), 
            pd.Series(ha_high, index=df.index), 
            pd.Series(ha_low, index=df.index), 
            pd.Series(ha_close.values, index=df.index))

def apply_ohlc_transformation(df, mode=1):
    """
    Handles exactly 5 pure mathematical OHLC Transformations:
    Mode 1: Raw Candles
    Mode 2: Mid-Body (OC/2) Pure Math Candles
    Mode 3: Full Range (OHLC/4) Pure Math Candles
    Mode 4: Standard Heikin-Ashi Candles
    Mode 5: Master Ensemble Average of Modes 1, 2, 3, and 4
    """
    if df.empty:
        return df
        
    raw_o, raw_h, raw_l, raw_c = df['Open'].copy(), df['High'].copy(), df['Low'].copy(), df['Close'].copy()
    
    if mode == 1:
        # Mode 1 returns the pure raw columns unmodified
        pass
        
    elif mode == 2:
        # Mode 2 body close shifts strictly to the OC/2 midpoint
        df['Close'] = (raw_o + raw_c) / 2
        
    elif mode == 3:
        # Mode 3 body close shifts strictly to the OHLC/4 calculation
        df['Close'] = (raw_o + raw_h + raw_l + raw_c) / 4
        
    elif mode == 4:
        # Mode 4 applies recursive Heikin-Ashi arrays
        ha_o, ha_h, ha_l, ha_c = _get_ha_values(df)
        df['Open'], df['High'], df['Low'], df['Close'] = ha_o, ha_h, ha_l, ha_c
        
    elif mode == 5:
        # Mode 1 explicit configuration arrays
        m1_o, m1_h, m1_l, m1_c = raw_o, raw_h, raw_l, raw_c
        
        # Mode 2 explicit configuration arrays
        m2_o, m2_h, m2_l, m2_c = raw_o, raw_h, raw_l, (raw_o + raw_c) / 2
        
        # Mode 3 explicit configuration arrays
        m3_o, m3_h, m3_l, m3_c = raw_o, raw_h, raw_l, (raw_o + raw_h + raw_l + raw_c) / 4
        
        # Mode 4 explicit configuration arrays
        m4_o, m4_h, m4_l, m4_c = _get_ha_values(df)
        
        # Mode 5 Master Blend: Elements added together and divided by 4
        df['Open']  = (m1_o + m2_o + m3_o + m4_o) / 4
        df['High']  = (m1_h + m2_h + m3_h + m4_h) / 4
        df['Low']   = (m1_l + m2_l + m3_l + m4_l) / 4
        df['Close'] = (m1_c + m2_c + m3_c + m4_c) / 4
        
    return df

def fetch_yf_data(period=None, interval="1m", target_rows=60):
    """DYNAMIC HISTORICAL SLICE RETRIEVAL ENGINE FOR DATA WITH OHLC MODES"""
    ticker_obj = yf.Ticker(TICKER)
    df = pd.DataFrame()
    
    # Cleaned down to target required size since no moving average warming window is required
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
                    df.dropna(inplace=True)
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
        
    processed_df = apply_ohlc_transformation(df.copy(), mode=OHLC_MODE)
    
    # VERIFIED: Moving Average calculations completely scrubbed from data compilation
    return processed_df.tail(target_rows)
