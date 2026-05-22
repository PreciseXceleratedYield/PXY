# sysstrndpxy.py
import pandas as pd 
import numpy as np 

try: 
    from sysdtafpxy import fetch_yf_data 
except ImportError: 
    def fetch_yf_data(): 
        # Deterministic default mock data for baseline isolation testing
        return pd.DataFrame({'Close': np.linspace(10, 20, 100) + np.random.randn(100) * 0.5}) 

# INTEGRATED PIPELINE CONNECTIONS
try:
    from syskatrpxy import calculate_atr, calculate_dynamic_k
except ImportError:
    def calculate_atr(df, period=14):
        high, low, close = df.get('High', df['Close']), df.get('Low', df['Close']), df['Close']
        tr = pd.concat([high - low, (high - close.shift(1)).abs(), (low - close.shift(1)).abs()], axis=1).max(axis=1)
        return tr.rolling(window=period, min_periods=1).mean().fillna(20.0)
    def calculate_dynamic_k(df, **kwargs):
        return 3.0

# Global Config 
DEBUG_MODE = True 
MA_TYPE = "SMA"  # Set to "TSMA" or "SMA" 

# 🔄 FIXED INDICES TYPE CASTING FOR SLICING
def calculate_sma_42(series: pd.Series, dynamic_lengths: np.ndarray) -> np.ndarray: 
    y = series.to_numpy() 
    n = len(y) 
    sma_output = np.empty(n) 
    sma_output[:] = np.nan
    for i in range(n): 
        raw_L = dynamic_lengths[i]
        if np.isnan(raw_L):
            continue
        L = int(raw_L) # 🎯 CRITICAL FIX: Explicitly cast to pure integer type for slicing
        if i < L - 1:
            continue
        y_slice = y[i - L + 1 : i + 1] 
        sma_output[i] = y_slice.mean() 
    return sma_output 

# 🔄 FIXED INDICES TYPE CASTING FOR SLICING
def calculate_tsma_42(series: pd.Series, dynamic_lengths: np.ndarray) -> np.ndarray: 
    y = series.to_numpy() 
    n = len(y) 
    tsma_output = np.empty(n)
    tsma_output[:] = np.nan
    for i in range(n): 
        raw_L = dynamic_lengths[i]
        if np.isnan(raw_L):
            continue
        L = int(raw_L) # 🎯 CRITICAL FIX: Explicitly cast to pure integer type for slicing
        if i < L - 1:
            continue
        y_slice = y[i - L + 1 : i + 1] 
        x = np.arange(L) 
        x_mean = x.mean() 
        y_mean = y_slice.mean() 
        denom = np.sum((x - x_mean) ** 2) 
        if denom == 0: 
            tsma_output[i] = y_slice[-1] 
            continue 
        slope = np.sum((x - x_mean) * (y_slice - y_mean)) / denom 
        intercept = y_mean - slope * x_mean 
        tsma_output[i] = slope * (L - 1) + intercept 
    return tsma_output 

def calculate_supertrend(df: pd.DataFrame) -> pd.DataFrame: 
    """ PXY® Engine: Clean MA Matrix with Crossover Signals & Ongoing States. """ 
    # A. Extract dynamic length variables from syskatrpxy matching your Pine indicators
    atr_series = calculate_atr(df, period=14).to_numpy()
    k_factor = calculate_dynamic_k(df, atr_period=14)
    
    n = len(df)
    dynamic_lengths = np.empty(n)
    dynamic_lengths[:] = np.nan
    for i in range(n):
        if not np.isnan(atr_series[i]):
            # 🎯 SAFETY FIX: Force rounding conversions to standard float/int before bounds checking
            L = round(float(atr_series[i] * k_factor))
            dynamic_lengths[i] = float(max(3, min(100, L)))

    # B. Generate the base line passing the dynamic lengths through
    if MA_TYPE.upper() == "SMA": 
        base_ma_line = calculate_sma_42(df['Close'], dynamic_lengths) 
    else: 
        base_ma_line = calculate_tsma_42(df['Close'], dynamic_lengths) 
        
    # Boundary tracking set strictly to the Moving Average line alone
    df['ST'] = base_ma_line 
    df['c1'] = df['Close'].shift(1) 
    df['st_prev'] = df['ST'].shift(1) 
    
    tail_size = min(50, len(df)) 
    df = df.tail(tail_size).copy() 
    df['bar_count'] = np.arange(1, tail_size + 1) 
    
    st_trend = [] 
    for i in range(len(df)): 
        if i == 0: 
            st_trend.append("SIDE") 
            continue 
        c0 = df['Close'].iloc[i] 
        c1 = df['c1'].iloc[i] 
        st_curr = df['ST'].iloc[i] 
        st_prev = df['st_prev'].iloc[i] 
        
        if pd.isna(st_curr) or pd.isna(st_prev) or pd.isna(c1): 
            st_trend.append("SIDE") 
            continue 
            
        # Clean MA Crossover Logic
        cross_above = (c0 > st_curr) and (c1 <= st_prev) 
        cross_below = (c0 < st_curr) and (c1 >= st_prev) 
        
        # State Matrix Assignment
        if cross_above: 
            new_trend = "AVGB" 
        elif cross_below: 
            new_trend = "AVGS" 
        else: 
            new_trend = "BULL" if (c0 > st_curr) else "BEAR" 
            
        st_trend.append(new_trend) 
        
    df['ST_Trend'] = st_trend 
    return df 

if __name__ == "__main__": 
    print(f"=== [TIER 1] {MA_TYPE} Adaptive Engine Local Math Test ===") 
    df_st = calculate_supertrend(fetch_yf_data())
    print(f"TERMINAL STATE STRUCTURAL METRIC: {df_st['ST_Trend'].iloc[-1]}")


