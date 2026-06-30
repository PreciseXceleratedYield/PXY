# syskatrpxy.py
import pandas as pd
import numpy as np
from sysdtafpxy import fetch_yf_data
from syscnfgpxy import PARAMS
from colorama import Fore, Style, init

init(autoreset=True)

ATR_PERIOD = 14
K_MIN = 1
K_MAX = 3
TOTAL_WIDTH = 42
MIN_FLOOR = 5 # Adjusted: New production absolute floor layer

# Production scale anchors
ATR_SCALE_MIN = 6.0
ATR_SCALE_MAX = 12.0

# Synchronized fallback safety anchors for errors or missing data
FALLBACK_ATR = 9
FALLBACK_K = 2.0

def calculate_atr(df: pd.DataFrame, period=ATR_PERIOD) -> pd.Series:
    # Return a safe series containing fallback defaults if dataframe is unusable
    if df is None or df.empty or len(df) < 1:
        return pd.Series([float(FALLBACK_ATR)])
    
    df_local = df.copy()
    
    # Secure time index parsing
    if not isinstance(df_local.index, pd.DatetimeIndex):
        df_local.index = pd.to_datetime(df_local.index)
        
    # Guard against missing essential columns
    required_cols = ['High', 'Low', 'Close']
    if not all(col in df_local.columns for col in required_cols):
        # FIXED: Added fallback 'None' to the ternary operator
        return pd.Series([float(FALLBACK_ATR)], index=df_local.index if not df_local.empty else None)
        
    high, low, close = df_local['High'], df_local['Low'], df_local['Close']
    prev_close = close.shift(1)
    
    # Calculate Standard True Range
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs()
    ], axis=1).max(axis=1)
    
    # Group rolling window mean computations by session dates
    # to perfectly replicate TradingView chart indicator breaks at 9:15 AM
    date_groups = df_local.index.date
    atr = tr.groupby(date_groups, group_keys=False).apply(
        lambda x: x.rolling(window=period, min_periods=1).mean()
    )
    
    # FIXED: If the market flatlines or values are NaN, it safely drops down to your floor of 5.
    return atr.apply(lambda x: float(MIN_FLOOR) if (x == 0 or pd.isna(x)) else max(float(MIN_FLOOR), x))

def calculate_dynamic_k(df: pd.DataFrame, atr_period=ATR_PERIOD, k_min=K_MIN, k_max=K_MAX) -> float:
    if df is None or df.empty:
        return FALLBACK_K
        
    atr_series = calculate_atr(df, period=atr_period)
    if atr_series.empty:
        return FALLBACK_K
        
    latest_atr = atr_series.iloc[-1]
    
    # FIXED: In the event of a data problem or a 0 value, return safe fallback baseline K of 2.0
    if pd.isna(latest_atr) or latest_atr == 0:
        return FALLBACK_K
        
    # Strictly cap input ATR parameters between 6 and 12
    clamped_atr = max(ATR_SCALE_MIN, min(latest_atr, ATR_SCALE_MAX))
    
    # Normalized position between 0.0 and 1.0
    norm_atr = (clamped_atr - ATR_SCALE_MIN) / (ATR_SCALE_MAX - ATR_SCALE_MIN)
    
    # Exponential scaling logic using natural base (e) growth
    k_dynamic = k_min + (k_max - k_min) * ((np.exp(norm_atr) - 1) / (np.e - 1))
    
    return round(k_dynamic, 2)

if __name__ == "__main__":
    try:
        df = fetch_yf_data()
    except Exception:
        df = None
        
    # Force safety fallback triggers on data fetch errors
    if df is not None and not df.empty and len(df) >= 1:
        atr_series = calculate_atr(df)
        dynamic_k = calculate_dynamic_k(df)
        
        val = atr_series.iloc[-1] if not atr_series.empty else float(FALLBACK_ATR)
        
        # Check if calculated value is invalid; if so, trigger fallback layout
        if pd.isna(val) or val == 0:
            val = float(FALLBACK_ATR)
            dynamic_k = FALLBACK_K
            
        atr_display = int(np.round(val))
        left_text = f"ATR:{atr_display}"
        right_text = f"K:{dynamic_k}"
        spacing = " " * max(TOTAL_WIDTH - len(left_text) - len(right_text), 1)
        print(left_text + spacing + right_text)
    else:
        # FIXED: Synchronized static empty workspace layout to match requested fallback parameters
        left_text = f"ATR:{FALLBACK_ATR}"
        right_text = f"K:{FALLBACK_K}"
        spacing = " " * max(TOTAL_WIDTH - len(left_text) - len(right_text), 1)
        print(left_text + spacing + right_text)
