"""# sysstrndpxy.py """
import pandas as pd
import numpy as np
from sysdtafpxy import fetch_yf_data

# Global Config
DEBUG_MODE = True
MA_TYPE = "TSMA"  # <--- SWITCH SWITCH: Set to "TSMA" or "SMA"

def calculate_sma_42(series: pd.Series) -> np.ndarray:
    """
    Calculates a strict 42-row Simple Moving Average (SMA).
    Uses a dynamic rolling lookback window capped at 42 rows to prevent NaN fallback.
    """
    y = series.to_numpy()
    n = len(y)
    sma_output = np.empty(n)
    
    for i in range(n):
        # Window size matches row count, capped at 42 lookback rows
        current_window = min(i + 1, 42)
        y_slice = y[i - current_window + 1 : i + 1]
        sma_output[i] = y_slice.mean()
        
    return sma_output

def calculate_tsma_42(series: pd.Series) -> np.ndarray:
    """
    Calculates a strict 42-row Time Series Moving Average (Linear Regression).
    Uses a fast linear algebra slope projection over the pre-padded matrix rows.
    """
    y = series.to_numpy()
    n = len(y)
    tsma_output = np.empty(n)

    # First row fallback (cannot regress a single isolated point)
    tsma_output[0] = y[0]

    # Linear algebra loop over the index rows
    for i in range(1, n):
        # Window size matches row count, capped at 42 lookback rows
        current_window = min(i + 1, 42)
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
    PXY® Engine: Pure Moving Average 42 Price Midpoint Engine
    - Slices down to a strict 50-row tail matrix vector.
    - Runs completely on upstream pre-transformed Mode 5 datasets.
    - Forces the ST baseline to track the 50/50 blend of Selected MA and Live Close.
    """
    # Slice the clean matrix down to exactly 50 rows
    df = df.tail(50).copy()

    # Create sequential bar tracker integers from 1 to 50
    df['bar_count'] = np.arange(1, 51)

    # Global Router Switch Evaluation Layer
    if MA_TYPE.upper() == "SMA":
        base_ma_line = calculate_sma_42(df['Close'])
    else:
        base_ma_line = calculate_tsma_42(df['Close'])

    # NEW ST LINE MATH: Pure 1:1 price weight fusion blending selected MA with Live Close
    df['ST'] = (base_ma_line + df['Close'].to_numpy()) / 2.0

    # State-machine trend tracking loop matching the Pine engine
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
    print(f"=== Upgraded Mode 5 {MA_TYPE} 42 Midpoint Engine Self-Test ===")
    trend_signal, st_line_value = get_signal()
    print(f"CURRENT SYSTEM SIGNAL: {trend_signal} | LINE METRIC: {st_line_value:.2f}")




