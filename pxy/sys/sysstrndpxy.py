# sysstrndpxy.py
import pandas as pd 
import numpy as np 

try: 
    from sysdtafpxy import fetch_yf_data 
except ImportError: 
    def fetch_yf_data(): 
        # Deterministic default mock data for baseline isolation testing
        return pd.DataFrame({'Close': np.linspace(10, 20, 100) + np.random.randn(100) * 0.5}) 

# Global Config 
DEBUG_MODE = True 
MA_TYPE = "TSMA"  # Set to "TSMA" or "SMA" 

def calculate_sma_42(series: pd.Series) -> np.ndarray: 
    y = series.to_numpy() 
    n = len(y) 
    sma_output = np.empty(n) 
    for i in range(n): 
        current_window = min(i + 1, 42) 
        y_slice = y[i - current_window + 1 : i + 1] 
        sma_output[i] = y_slice.mean() 
    return sma_output 

def calculate_tsma_42(series: pd.Series) -> np.ndarray: 
    y = series.to_numpy() 
    n = len(y) 
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
    """ PXY® Engine: Clean 42 MA Matrix with Crossover Signals & Ongoing States. """ 
    if MA_TYPE.upper() == "SMA": 
        base_ma_line = calculate_sma_42(df['Close']) 
    else: 
        base_ma_line = calculate_tsma_42(df['Close']) 
        
    # Boundary tracking set strictly to the 42 Moving Average line alone
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
            
        # Clean 42 MA Crossover Logic
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
    print(f"=== [TIER 1] {MA_TYPE} 42 Engine Local Math Test ===") 
    df_st = calculate_supertrend(fetch_yf_data())
    print(f"TERMINAL STATE STRUCTURAL METRIC: {df_st['ST_Trend'].iloc[-1]}")

