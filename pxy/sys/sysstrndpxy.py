# sysstrndpxy.py
import pandas as pd 
import numpy as np 

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
    """ PXY® Engine: Cleaned single ST line processing driver matrix. """ 
    if df is None or df.empty:
        return pd.DataFrame()

    # Safe working copy to keep memory context isolated
    df = df.copy()

    if MA_TYPE.upper() == "SMA": 
        base_ma_line = calculate_sma_42(df['Close']) 
    else: 
        base_ma_line = calculate_tsma_42(df['Close']) 
        
    # Formulate Highest High and Lowest Low channels
    hh_42 = df['High'].rolling(window=42, min_periods=1).max().to_numpy()
    ll_42 = df['Low'].rolling(window=42, min_periods=1).min().to_numpy()
    
    # 🎯 ONLY KEEP ST LINE - REMOVED ALL OTHER CHANNELS
    df['pxy_st_line'] = (base_ma_line + hh_42 + ll_42 + df['Close']) / 4.0
    
    # Dashboard Compatibility Reference Keys
    df['ST'] = df['pxy_st_line'] 
    df['c1'] = df['Close'].shift(1) 
    df['st_prev'] = df['ST'].shift(1) 

    # Extract NumPy arrays for ultra-fast loop routing
    m5_c  = df['Close'].to_numpy()
    m5_o  = df['Open'].to_numpy()
    st    = df['pxy_st_line'].to_numpy()
    
    st_trend_full = [] 
    n = len(df)
    
    for i in range(n): 
        if i < 1: 
            st_trend_full.append("BULL" if m5_c[i] >= st[i] else "BEAR") 
            continue 
            
        c0 = m5_c[i]
        c1 = m5_c[i-1]
        o0 = m5_o[i]
        o1 = m5_o[i-1]
        
        # 1. Pure Center Line Crossovers
        cross_buy  = (c0 > st[i]) and (c1 <= st[i-1])
        cross_sell = (c0 < st[i]) and (c1 >= st[i-1])
        
        # 2. Candle Color Flip Metrics (Red <-> Green Body Changes)
        is_curr_green = (c0 > o0)
        is_prev_green = (c1 > o1)
        
        # Detect shifts in candle direction
        red_to_green = is_curr_green and not is_prev_green
        green_to_red = not is_curr_green and is_prev_green
        
        # ==============================================================================
        # 🎯 EXCLUSIVE PRIORITY SIGNAL EXECUTION MATRIX
        # ==============================================================================
        if cross_buy: 
            new_trend = "CROSSBUY" 
        elif cross_sell: 
            new_trend = "CROSSSELL" 
        elif red_to_green:
            new_trend = "FORCEBUY"     # Context-based signal: Candle flipped green
        elif green_to_red:
            new_trend = "FORCESELL"    # Context-based signal: Candle flipped red
        else: 
            # Baseline Ongoing Trend Fallback
            new_trend = "BULL" if (c0 >= st[i]) else "BEAR" 
            
        st_trend_full.append(new_trend) 
        
    df['ST_Trend'] = st_trend_full 
    
    tail_size = min(50, len(df)) 
    return df.tail(tail_size).copy() 

if __name__ == "__main__": 
    print(f"=== [TIER 1] Single ST Line Matrix with Context Candle Flip Engine Ready ===")



