# sysstrndpxy.py
import pandas as pd
import numpy as np
import pytz
from sysdtafpxy import fetch_yf_data

DEBUG_MODE = True

def calculate_supertrend(df: pd.DataFrame) -> pd.DataFrame:
    """
    PXY® Engine: Fixed Anchor + Smooth IST Merge Logic
    Slices and processes a strict 50-row rolling frame window.
    """
    # Force a strict trailing 50-row window from the upstream feed
    df = df.tail(50).copy()
    
    # 1. Enforce Datetime Index Alignment
    if not isinstance(df.index, pd.DatetimeIndex):
        date_col = next((c for c in ['Date', 'Datetime', 'timestamp', 'time'] if c in df.columns), None)
        if date_col:
            df[date_col] = pd.to_datetime(df[date_col])
            df.set_index(date_col, inplace=True)
            
    # 2. Timezone synchronization check
    if df.index.tz is None:
        df.index = df.index.tz_localize('UTC').tz_convert('Asia/Kolkata')
    elif str(df.index.tz) != 'Asia/Kolkata':
        df.index = df.index.tz_convert('Asia/Kolkata')
        
    # 3. Position-based Matrix Metrics for exactly 50 rows
    df['bar_count'] = np.arange(1, 51)
    
    # Cumulative session mean over the 50-row space
    df['session_mean'] = df['Close'].expanding(min_periods=1).mean()
    
    # 50 SMA rolling window matches exactly 50 rows matrix sizing
    df['sma_50'] = df['Close'].rolling(window=50, min_periods=1).mean()
    df['python_hybrid'] = (df['session_mean'] + df['sma_50']) / 2
    
    # 4. Stabilized Anchor Logic
    # Pulls strictly from index 0 of the current 50-row matrix
    first_bar_open = df['Open'].iloc[0]
    first_bar_close = df['Close'].iloc[0]
    first_bar_high = df['High'].iloc[0]
    first_bar_low = df['Low'].iloc[0]
    
    anchor_value = first_bar_high if first_bar_close > first_bar_open else first_bar_low
    df['anchor'] = anchor_value
    
    # 5. Blend factor calculations (15 to 45 scaling bounds)
    df['blend_factor'] = ((df['bar_count'] - 15) / 30.0).clip(0, 1)
    
    df['ST'] = np.where(
        df['bar_count'] <= 15, 
        df['anchor'], 
        np.where(
            df['bar_count'] <= 45, 
            (df['anchor'] * (1 - df['blend_factor'])) + (df['python_hybrid'] * df['blend_factor']), 
            df['python_hybrid']
        )
    )
    
    # 6. Optimized Trend Matrix Generation
    st_trend = []
    prev_trend = "SIDE"
    
    for i in range(len(df)):
        curr_close = df['Close'].iloc[i]
        curr_line = df['ST'].iloc[i]
        
        if pd.isna(curr_line):
            st_trend.append("SIDE")
            continue
            
        if curr_close > curr_line:
            new_trend = "UP" if prev_trend in ["UP", "BUY"] else "BUY"
        elif curr_close < curr_line:
            new_trend = "DOWN" if prev_trend in ["DOWN", "SELL"] else "SELL"
        else:
            new_trend = "SIDE"
            
        st_trend.append(new_trend)
        prev_trend = new_trend
        
    df['ST_Trend'] = st_trend
    return df

def get_signal(df=None):
    """Downstream communication port processing execution metrics"""
    if df is None:
        df = fetch_yf_data()
        
    if df is None or df.empty:
        return "NONE", 0.0
        
    try:
        df_st = calculate_supertrend(df)
        last = df_st.iloc[-1]
        return str(last['ST_Trend']), float(last['ST'])
    except Exception as e:
        if DEBUG_MODE:
            print(f"PXY Error: {e}")
        return "NONE", 0.0

if __name__ == "__main__":
    print("=== Supertrend Signal Engine Self-Test ===")
    trend_signal, st_line_value = get_signal()
    print(f"CURRENT SYSTEM SIGNAL: {trend_signal} | LINE METRIC: {st_line_value}")

