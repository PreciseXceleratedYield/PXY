# syskatrpxy.py 
import pandas as pd 
import numpy as np 
from sysdtafpxy import fetch_yf_data 
from syscnfgpxy import PARAMS 
from colorama import Fore, Style, init 

init(autoreset=True) 

# -------------------- Hardcoded constants -------------------- 
ATR_PERIOD = 14 
K_MIN = 1 
K_MAX = 3 
TOTAL_WIDTH = 42 

# -------------------- ATR Calculation -------------------- 
def calculate_atr(df: pd.DataFrame, period=ATR_PERIOD) -> pd.Series: 
    current_len = len(df)
    effective_period = period if current_len >= period else max(1, current_len)

    high, low, close = df['High'], df['Low'], df['Close'] 
    prev_close = close.shift(1) 
    
    tr = pd.concat([ 
        high - low, 
        (high - prev_close).abs(), 
        (low - prev_close).abs() 
    ], axis=1).max(axis=1) 
    
    atr = tr.rolling(effective_period).mean() 
    return atr.apply(lambda x: 20.0 if (x == 0 or pd.isna(x)) else x) 

# -------------------- Dynamic K Calculation -------------------- 
def calculate_dynamic_k(df: pd.DataFrame, atr_period=ATR_PERIOD, k_min=K_MIN, k_max=K_MAX) -> float: 
    atr_series = calculate_atr(df, period=atr_period) 
    
    if atr_series.empty:
        return 2.0

    latest_atr = atr_series.iloc[-1] 
    
    # DATA FIX: Extract NumPy values directly to prevent short array index tracking errors
    atr_subset = atr_series.iloc[-atr_period:].values if len(atr_series) >= atr_period else atr_series.values 
    atr_mean = atr_subset.mean() if len(atr_subset) > 0 else 20.0 
    
    if latest_atr <= 20.0 or atr_mean <= 20.0 or pd.isna(latest_atr): 
        return 2.0 
        
    k_dynamic = k_min + (k_max - k_min) * (latest_atr / atr_mean) 
    k_dynamic = max(min(k_dynamic, k_max), k_min) 
    return round(k_dynamic, 2) 

if __name__ == "__main__": 
    df = fetch_yf_data() 
    if df is not None and not df.empty and len(df) >= 1: 
        atr_series = calculate_atr(df) 
        dynamic_k = calculate_dynamic_k(df) 
        val = atr_series.iloc[-1] if not atr_series.empty else 20.0
        
        atr_display = int(val) if (not pd.isna(val) and val != 0) else 2 
        left_text = f"ATR:{atr_display}" 
        right_text = f"K:{dynamic_k}" 
        space_width = TOTAL_WIDTH - len(left_text) - len(right_text) 
        spacing = " " * max(space_width, 1) 
        print(left_text + spacing + right_text) 
    else: 
        print(f"ATR:20" + (" " * 28) + "K:2.0")

