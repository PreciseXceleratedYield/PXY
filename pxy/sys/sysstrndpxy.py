# sysstrndpxy.py
import pandas as pd
import numpy as np
from sysdtafpxy import fetch_yf_data

DEBUG_MODE = True

def calculate_tsma(series: pd.Series) -> np.ndarray:
    """
    Calculates a strict 50-row Time Series Moving Average (Linear Regression).
    Uses a fast linear algebra slope projection over the pre-padded matrix rows.
    """
    y = series.to_numpy()
    n = len(y)
    tsma_output = np.empty(n)
    
    # First row fallback (cannot regress a single isolated point)
    tsma_output[0] = y[0]
    
    # Linear algebra loop over the index rows
    for i in range(1, n):
        # Window size matches row count, capped at 50 lookback rows
        current_window = min(i + 1, 50)
        y_slice = y[i - current_window + 1 : i + 1]
        
        # Build independent time grid index vector x: [0, 1, 2... window_len - 1]
        x = np.arange(current_window)
        x_mean = x.mean()
        y_mean = y_slice.mean()
        
        # Calculate Ordinary Least Squares regression parameters
        slope = np.sum((x - x_mean) * (y_slice - y_mean)) / np.sum((x - x_mean) ** 2)
        intercept = y_mean - slope * x_mean
        
        # Project endpoint location line value at current position index i
        tsma_output[i] = slope * (current_window - 1) + intercept
        
    return tsma_output

def calculate_supertrend(df: pd.DataFrame) -> pd.DataFrame:
    """
    PXY® Engine: Fixed Anchor + Smooth IST Merge Logic
    Processes the strict 50-row tail vector generated from the upstream feed.
    """
    # Slice the clean matrix down to exactly 50 rows
    df = df.tail(50).copy()
    
    # Create sequential bar tracker integers from 1 to 50
    df['bar_count'] = np.arange(1, 51)
    
    # Calculate tracking baseline profiles
    df['session_mean'] = df['Close'].expanding(min_periods=1).mean()
    df['tsma_50'] = calculate_tsma(df['Close'])
    df['python_hybrid'] = (df['session_mean'] + df['tsma_50']) / 2
    
    # Extract Anchor Levels cleanly from Row 1 using positional index selectors
    first_bar_open = df['Open'].iloc[0]
    first_bar_close = df['Close'].iloc[0]
    
    anchor_value = df['High'].iloc[0] if first_bar_close > first_bar_open else df['Low'].iloc[0]
    df['anchor'] = anchor_value
    
    # Apply three-phase structural blending configurations
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
    
    # State-machine trend tracking loop
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
    print("=== Cleaned TSMA(50) Supertrend Signal Engine Self-Test ===")
    trend_signal, st_line_value = get_signal()
    print(f"CURRENT SYSTEM SIGNAL: {trend_signal} | LINE METRIC: {st_line_value}")


