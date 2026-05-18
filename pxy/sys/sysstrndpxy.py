import pandas as pd 
import numpy as np 
# Replaced mock import with safe fallback template
try:
    from sysdtafpxy import fetch_yf_data
except ImportError:
    def fetch_yf_data(): return pd.DataFrame({'Close': np.random.randn(100)})

# Global Config 
DEBUG_MODE = True 
MA_TYPE = "SMA"  # <--- SWITCH SWITCH: Set to "TSMA" or "SMA"

def calculate_sma_42(series: pd.Series) -> np.ndarray:
    """ Calculates a strict 42-row Simple Moving Average (SMA). """
    y = series.to_numpy()
    n = len(y)
    sma_output = np.empty(n)
    for i in range(n):
        current_window = min(i + 1, 42)
        y_slice = y[i - current_window + 1 : i + 1]
        sma_output[i] = y_slice.mean()
    return sma_output

def calculate_tsma_42(series: pd.Series) -> np.ndarray:
    """ Calculates a strict 42-row Time Series Moving Average (Linear Regression). """
    y = series.to_numpy()
    n = len(y)
    # FIX 1: Use .copy() to prevent mutating original DataFrame historical data
    tsma_output = y.copy() 
    for i in range(1, n):
        current_window = min(i + 1, 42)
        y_slice = y[i - current_window + 1 : i + 1]
        x = np.arange(current_window)
        x_mean = x.mean()
        y_mean = y_slice.mean()
        
        denom = np.sum((x - x_mean) ** 2)
        if denom == 0:
            tsma_output[i] = y_slice[-1]
            continue
            
        slope = np.sum((x - x_mean) * (y_slice - y_mean)) / denom
        intercept = y_mean - slope * x_mean
        tsma_output[i] = slope * (current_window - 1) + intercept
    return tsma_output

def calculate_supertrend(df: pd.DataFrame) -> pd.DataFrame:
    """ PXY® Engine: Multi-Layer Cross and Flip State Matrix. """
    # 1. Evaluate Core Moving Average arrays
    if MA_TYPE.upper() == "SMA":
        base_ma_line = calculate_sma_42(df['Close'])
    else:
        base_ma_line = calculate_tsma_42(df['Close'])
        
    # 2. Inject Live Price Influence Smoothing Step 
    df['ST'] = (base_ma_line + df['Close'].to_numpy()) / 2.0
    
    # FIX 2: Compute shift context vectors globally BEFORE slicing to preserve index integrity
    df['c1'] = df['Close'].shift(1)
    df['c2'] = df['Close'].shift(2)
    df['st_prev'] = df['ST'].shift(1)
    
    # FIX 3: Dynamic tail sizing protects against short/newly-listed asset datasets
    tail_size = min(50, len(df))
    df = df.tail(tail_size).copy()
    df['bar_count'] = np.arange(1, tail_size + 1)
    
    st_trend = []
    for i in range(len(df)):
        # Handle start boundary edge case loops safely
        if i == 0:
            st_trend.append("SIDE")
            return df # Exit early if data structure contains only 1 row
            
        c0 = df['Close'].iloc[i]
        c1 = df['c1'].iloc[i]
        c2 = df['c2'].iloc[i]
        st_curr = df['ST'].iloc[i]
        st_prev = df['st_prev'].iloc[i]
        
        if pd.isna(st_curr) or pd.isna(st_prev) or pd.isna(c1):
            st_trend.append("SIDE")
            continue
            
        # Layer A: Strict Line Crossover Reference Flips
        cross_above = (c0 > st_curr) and (c1 <= st_prev)
        cross_below = (c0 < st_curr) and (c1 >= st_prev)
        
        # Layer B: Strict Internal Candle Price Color Transitions
        color_flip_green = (c0 > c1) and not (not pd.isna(c2) and c1 > c2)
        color_flip_red = (c0 < c1) and not (not pd.isna(c2) and c1 < c2)
        
        # Layer C: Routing Evaluation Matrix
        if cross_above:
            new_trend = "CROSSBUY"
        elif cross_below:
            new_trend = "CROSSSELL"
        elif color_flip_green and (c0 > st_curr):
            new_trend = "TRENDBUY"
        elif color_flip_red and (c0 < st_curr):
            new_trend = "TRENDSELL"
        else:
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



