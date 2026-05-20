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
MA_TYPE = "SMA"  # Set to "TSMA" or "SMA" 

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
    """ Reconfigured Engine: Very simple 42 SMA state mapping alone. """ 
    if MA_TYPE.upper() == "SMA": 
        base_ma_line = calculate_sma_42(df['Close']) 
    else: 
        base_ma_line = calculate_tsma_42(df['Close']) 
        
    # Strictly use the base 42 Moving Average line alone as our boundary
    df['ST'] = base_ma_line 
    
    tail_size = min(50, len(df)) 
    df = df.tail(tail_size).copy() 
    df['bar_count'] = np.arange(1, tail_size + 1) 
    
    st_trend = [] 
    for i in range(len(df)): 
        c0 = df['Close'].iloc[i] 
        st_curr = df['ST'].iloc[i] 
        
        if pd.isna(st_curr): 
            st_trend.append("SIDE") 
            continue 
            
        # Clean structural mapping: Simple 42 Moving Average boundary comparison
        if c0 >= st_curr: 
            new_trend = "BULL" 
        else: 
            new_trend = "BEAR" 
            
        st_trend.append(new_trend) 
        
    df['ST_Trend'] = st_trend 
    return df 

if __name__ == "__main__": 
    print(f"=== [TIER 1] {MA_TYPE} 42 Engine Local Math Test ===") 
    df_st = calculate_supertrend(fetch_yf_data())
    print(f"TERMINAL STATE STRUCTURAL METRIC: {df_st['ST_Trend'].iloc[-1]}")






