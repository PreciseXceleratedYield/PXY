# sysstrndpxy.py
import pandas as pd 
import numpy as np 

try: 
    from sysdtafpxy import fetch_yf_data 
except ImportError: 
    def fetch_yf_data(): 
        np.random.seed(42)
        n = 150
        return pd.DataFrame({
            'Open': np.linspace(10, 20, n) + np.random.randn(n) * 0.5,
            'High': np.linspace(10, 20, n) + np.random.randn(n) * 0.5 + 0.5,
            'Low': np.linspace(10, 20, n) + np.random.randn(n) * 0.5 - 0.5,
            'Close': np.linspace(10, 20, n) + np.random.randn(n) * 0.5
        })

# Global Config 
DEBUG_MODE = True 
MA_TYPE = "TSMA"  

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
    """ PXY® Engine: Simplified 42 MA Matrix with Clean Crossovers & Flip Breakouts. """ 
    if MA_TYPE.upper() == "SMA": 
        base_ma_line = calculate_sma_42(df['Close']) 
    else: 
        base_ma_line = calculate_tsma_42(df['Close']) 
        
    # 1. Formulate Highest High and Lowest Low channels
    hh_42 = df['High'].rolling(window=42, min_periods=1).max().to_numpy()
    ll_42 = df['Low'].rolling(window=42, min_periods=1).min().to_numpy()
    
    # 2. Reference Lines 
    df['pxy_st_line']  = (base_ma_line + hh_42 + ll_42 + df['Close']) / 4.0
    df['pxy_st_no_ll'] = (base_ma_line + hh_42 + df['Close']) / 3.0
    df['pxy_st_no_hh'] = (base_ma_line + ll_42 + df['Close']) / 3.0
    
    # Extract arrays
    m5_c  = df['Close'].to_numpy()
    st    = df['pxy_st_line'].to_numpy()
    no_ll = df['pxy_st_no_ll'].to_numpy()
    no_hh = df['pxy_st_no_hh'].to_numpy()
    
    st_trend_full = [] 
    n = len(df)
    
    for i in range(n): 
        if i < 1: 
            st_trend_full.append("SIDE") 
            continue 
            
        c0 = m5_c[i]
        c1 = m5_c[i-1]
        
        # Pure Line Crossovers
        cross_buy  = (c0 > st[i]) and (c1 <= st[i-1])
        cross_sell = (c0 < st[i]) and (c1 >= st[i-1])
        
        # Pure Boundary Breakout Signals (Your Intended Inversion Setup)
        force_buy  = (c0 > no_ll[i]) and (c1 <= no_ll[i-1])
        force_sell = (c0 < no_hh[i]) and (c1 >= no_hh[i-1])
        
        # Simplified State Assignment Hierarchy
        if force_buy:
            new_trend = "FORCESELL"   # Upper break out -> Intended flip to FORCESELL
        elif force_sell:
            new_trend = "FORCEBUY"    # Lower break down -> Intended flip to FORCEBUY
        elif cross_buy: 
            new_trend = "CROSSBUY" 
        elif cross_sell: 
            new_trend = "CROSSSELL" 
        else: 
            new_trend = "BULL" if (c0 > st[i]) else "BEAR" 
            
        st_trend_full.append(new_trend) 
        
    df['ST_Trend'] = st_trend_full 
    
    tail_size = min(50, len(df)) 
    df = df.tail(tail_size).copy() 
    return df 

if __name__ == "__main__": 
    print(f"=== [TIER 1] Simplified {MA_TYPE} 42 Engine Local Test ===") 
    df_st = calculate_supertrend(fetch_yf_data())
    print(f"LIVE CANDLE STATE METRIC: {df_st['ST_Trend'].iloc[-1]}")
