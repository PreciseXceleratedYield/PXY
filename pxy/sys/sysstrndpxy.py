import pandas as pd
import numpy as np
from sysdtafpxy import fetch_yf_data

# Global Config
DEBUG_MODE = True
MA_TYPE = "SMA" # <--- SWITCH SWITCH: Set to "TSMA" or "SMA"

def calculate_sma_42(series: pd.Series) -> np.ndarray:
    """
    Calculates a strict 42-row Simple Moving Average (SMA).
    Uses a dynamic rolling lookback window capped at 42 rows to prevent NaN fallback.
    """
    y = series.to_numpy()
    n = len(y)
    sma_output = np.empty(n)
    for i in range(n):
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
    tsma_output = y
    for i in range(1, n):
        current_window = min(i + 1, 42)
        y_slice = y[i - current_window + 1 : i + 1]
        x = np.arange(current_window)
        x_mean = x.mean()
        y_mean = y_slice.mean()
        slope = np.sum((x - x_mean) * (y_slice - y_mean)) / np.sum((x - x_mean) ** 2)
        intercept = y_mean - slope * x_mean
        tsma_output[i] = slope * (current_window - 1) + intercept
    return tsma_output

def calculate_supertrend(df: pd.DataFrame) -> pd.DataFrame:
    """
    PXY® Engine: Multi-Layer Cross and Flip State Matrix.
    Processes full background dataset vectors to guarantee matching index history.
    """
    # 1. Evaluate Core Moving Average arrays using the full historical price tail context
    if MA_TYPE.upper() == "SMA":
        base_ma_line = calculate_sma_42(df['Close'])
    else:
        base_ma_line = calculate_tsma_42(df['Close'])
    
    # 2. Inject the exact Live Price Influence Smoothing Step into the baseline array
    df['ST'] = (base_ma_line + df['Close'].to_numpy()) / 2.0

    # 3. Slices down to a strict 50-row tail matrix vector AFTER baseline processing is complete
    df = df.tail(50).copy()
    df['bar_count'] = np.arange(1, 51)

    # 4. State-machine trend tracking loop matching the fixed Pine engine flips 1:1
    st_trend = []
    
    for i in range(len(df)):
        # Handle start boundary edge case loops safely
        if i == 0:
            st_trend.append("SIDE")
            continue
            
        c0 = df['Close'].iloc[i]
        c1 = df['Close'].iloc[i-1]
        st_curr = df['ST'].iloc[i]
        st_prev = df['ST'].iloc[i-1]
        
        if pd.isna(st_curr) or pd.isna(st_prev):
            st_trend.append("SIDE")
            continue
            
        # Layer A: Strict Line Crossover Reference Flips
        cross_above = (c0 > st_curr) and (c1 <= st_prev)
        cross_below = (c0 < st_curr) and (c1 >= st_prev)
        
        # Layer B: Strict Internal Candle Price Color Transitions (Red -> Green / Green -> Red)
        color_flip_green = (c0 > c1) and not (i > 1 and df['Close'].iloc[i-1] > df['Close'].iloc[i-2])
        color_flip_red   = (c0 < c1) and not (i > 1 and df['Close'].iloc[i-1] < df['Close'].iloc[i-2])
        
        # Layer C: Routing Evaluation Matrix
        if cross_above:
            new_trend = "TB"
        elif cross_below:
            new_trend = "TS"
        elif color_flip_green and (c0 > st_curr):
            new_trend = "CB"
        elif color_flip_red and (c0 < st_curr):
            new_trend = "CS"
        else:
            # UPDATED: Replaced "UP" and "DOWN" with structural "BULL" and "BEAR" states
            new_trend = "BULL" if (c0 > st_curr) else "BEAR"
            
        st_trend.append(new_trend)
        
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


