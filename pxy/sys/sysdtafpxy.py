# sysstrndpxy.py
import warnings
import numpy as np
import pandas as pd
import yfinance as yf
from syscnfgpxy import TICKER, OHLC_MODE, TIMEZONE

# Silence future warning constraints completely
warnings.simplefilter(action='ignore', category=FutureWarning)

def get_recursive_ohlc4_ohlc(o, h, l, c):
    """
    Generates recursive OHLC/4 transformed candles matching the Pine Script:
    - Close (new_c) = (o + h + l + c) / 4
    - Open (new_o)  = previous candle's new_c (or current open if first row)
    - High (new_h)  = max of raw high, new_o, and new_c
    - Low (new_l)   = min of raw low, new_o, and new_c
    """
    n = len(c)
    mod_o = np.zeros(n)
    mod_h = np.zeros(n)
    mod_l = np.zeros(n)
    mod_c = np.zeros(n)
    
    # Calculate Close first since it depends strictly on raw values per row
    mod_c = (o + h + l + c) / 4.0
    
    # Process recursive layout sequentially due to historical dependencies
    for i in range(n):
        if i == 0:
            mod_o[i] = o[i]
        else:
            mod_o[i] = mod_c[i-1] # Previous Close becomes Next Open
            
        mod_h[i] = max(h[i], mod_o[i], mod_c[i])
        mod_l[i] = min(l[i], mod_o[i], mod_c[i])
        
    return mod_o, mod_h, mod_l, mod_c

def get_heikin_ashi_ohlc(o, h, l, c):
    """
    Generates simplified, non-recursive candles matching our Pine Script logic.
    - Open: Average of current open and current close
    - High/Low: Raw chart values
    - Close: Average of current OHLC
    """
    ha_c = (o + h + l + c) / 4.0
    ha_o = (o + c) / 2.0
    ha_h = h
    ha_l = l
    return ha_o, ha_h, ha_l, ha_c

def get_open_close_median_ohlc(o, c):
    """Generates flat candle Open-Close Midpoint OHLC matrices (oc/2)"""
    oc2 = (o + c) / 2
    return oc2, oc2, oc2, oc2

def get_momentum_ohlc(c):
    """Generates shift momentum OHLC matrices using prior close boundaries (c1 c0)"""
    c1 = np.empty_like(c)
    if len(c) > 0:
        c1 = c
        c1[1:] = c[:-1]
    return c1, c, c1, c

def get_3sma_oc2_ohlc(df, window=4):
    """Generates dynamic SMA OC/2 Pine chart calculation candles (Mode 6)"""
    sma_o = df['Open'].rolling(window=window, min_periods=1).mean().to_numpy()
    sma_c = df['Close'].rolling(window=window, min_periods=1).mean().to_numpy()
    
    n = len(df)
    ha_o = np.zeros(n)
    ha_c = np.zeros(n)
    
    for i in range(n):
        current_ha_c = (sma_o[i] + sma_c[i]) / 2.0
        ha_c[i] = current_ha_c
        
        if i == 0:
            ha_o[i] = current_ha_c
        else:
            ha_o[i] = (ha_o[i-1] + ha_c[i-1]) / 2.0
            
    ha_h = np.maximum(ha_o, ha_c)
    ha_l = np.minimum(ha_o, ha_c)
    return ha_o, ha_h, ha_l, ha_c

def get_flipped_geometry_ohlc(o, h, l, c):
    """Generates flipped candle geometry based on previous candle ranges (Mode 0)"""
    n = len(c)
    mod_o = np.zeros(n)
    mod_h = np.zeros(n)
    mod_l = np.zeros(n)
    mod_c = c.copy()

    prev_h = np.roll(h, 1)
    prev_l = np.roll(l, 1)
    prev_c = np.roll(c, 1)
    prev_range = prev_h - prev_l

    calc_quarter = prev_l + (prev_range * 0.25)
    calc_three_quarter = prev_l + (prev_range * 0.75)

    is_green = (c >= calc_three_quarter)

    mod_o = np.where(is_green, calc_quarter, calc_three_quarter)
    mod_h = np.where(is_green, h, np.maximum(h, prev_c))
    mod_l = np.where(is_green, np.minimum(l, prev_c), l)

    if n > 0:
        mod_o[0] = o[0]
        mod_h[0] = h[0]
        mod_l[0] = l[0]

    return mod_o, mod_h, mod_l, mod_c

def apply_ohlc_transformation(df, mode=1):
    """Transforms raw arrays into distinct, complete structural OHLC formats"""
    if df.empty: return df
    o = df['Open'].to_numpy()
    h = df['High'].to_numpy()
    l = df['Low'].to_numpy()
    c = df['Close'].to_numpy()
    
    if mode == 0:
        df['Open'], df['High'], df['Low'], df['Close'] = get_flipped_geometry_ohlc(o, h, l, c)
    elif mode == 1:
        return df
    elif mode == 2:
        df['Open'], df['High'], df['Low'], df['Close'] = get_heikin_ashi_ohlc(o, h, l, c)
    elif mode == 3:
        df['Open'], df['High'], df['Low'], df['Close'] = get_open_close_median_ohlc(o, c)
    elif mode == 4:
        df['Open'], df['High'], df['Low'], df['Close'] = get_momentum_ohlc(c)
    elif mode == 5:
        ha_o, ha_h, ha_l, ha_c = get_heikin_ashi_ohlc(o, h, l, c)
        oc2_o, oc2_h, oc2_l, oc2_c = get_open_close_median_ohlc(o, c)
        c1c0_o, c1c0_h, c1c0_l, c1c0_c = get_momentum_ohlc(c)
        df['Open'] = (o + ha_o + oc2_o + c1c0_o) / 4
        df['High'] = (h + ha_h + oc2_h + c1c0_h) / 4
        df['Low'] = (l + ha_l + oc2_l + c1c0_l) / 4
        df['Close'] = (c + ha_c + oc2_c + c1c0_c) / 4
    elif mode == 6:
        df['Open'], df['High'], df['Low'], df['Close'] = get_3sma_oc2_ohlc(df)
    elif mode == 7:
        # EXECUTE RECURSIVE OHLC/4 SYSTEM TRANSFORM
        df['Open'], df['High'], df['Low'], df['Close'] = get_recursive_ohlc4_ohlc(o, h, l, c)
    else:
        print(f"SYSTEM_WARNING | Mode {mode} unrecognized. Defaulting to Raw OHLC.")
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

def get_latest_data():
    """Returns the most recent live completed row using active config files parameters"""
    return fetch_yf_data().tail(1)

if __name__ == "__main__":
    print(f"=== PROCESSING RUNNING | ENGINE TARGET TICKER: {TICKER} ===")
    print(f"=== CURRENTLY ENFORCED DATA TRANSFORMATION MODE: {OHLC_MODE} ===")
    output_df = fetch_yf_data()
    if not output_df.empty:
        print(f"ENGINE_RUN_SUCCESS | Collected Rows Count: {len(output_df)}")

