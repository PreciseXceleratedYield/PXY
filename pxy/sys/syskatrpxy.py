# syskatrpxy.py
import pandas as pd
import numpy as np
from sysdtafpxy import fetch_yf_data
from syscnfgpxy import PARAMS
from colorama import Fore, Style, init

init(autoreset=True)

ATR_PERIOD = 14
K_MIN = 1.0
K_MAX = 3.0
TOTAL_WIDTH = 42

# Fallback constants if data is missing completely
FALLBACK_ATR = 1.0      # Set to 1.0 since the new ratio hovers around 1.0 for an average candle
FALLBACK_K = 2.0

def calculate_atr(df: pd.DataFrame, period=ATR_PERIOD) -> pd.Series:
    """Calculates your custom relative volatility ratio: ((High - Low) * 14) / 14-Period Sum."""
    if df is None or df.empty or len(df) < 1:
        return pd.Series([float(FALLBACK_ATR)])
    
    df_local = df.copy()
    
    # Secure time index parsing
    if not isinstance(df_local.index, pd.DatetimeIndex):
        df_local.index = pd.to_datetime(df_local.index)
        
    # Standardize column casing to prevent runtime KeyErrors
    df_local.columns = [col.capitalize() for col in df_local.columns]
    required_cols = ['High', 'Low']
    
    if not all(col in df_local.columns for col in required_cols):
        return pd.Series([float(FALLBACK_ATR)], index=df_local.index if not df_local.empty else None)
        
    high, low = df_local['High'], df_local['Low']
    
    # 1. Pure High minus Low calculation
    candle_range = high - low
    
    # Define date groups from index for session grouping
    date_groups = df_local.index.date
    
    # 2. Calculate the 14-period rolling sum
    rolling_sum = candle_range.groupby(date_groups, group_keys=False).apply(
        lambda x: x.rolling(window=period, min_periods=1).sum()
    )
    
    # 3. Apply your custom formula: (Current Range * 14) / Rolling Sum
    # Replacing 0 with NaN temporarily to prevent division-by-zero errors
    atr = (candle_range * 14) / rolling_sum.replace(0, np.nan)
    
    # Map NaNs back to fallback
    return atr.apply(lambda x: float(FALLBACK_ATR) if pd.isna(x) or x == 0 else float(x))

def calculate_dynamic_k(df: pd.DataFrame, atr_period=ATR_PERIOD, k_min=K_MIN, k_max=K_MAX) -> float:
    """Calculates inverse exponential K value scaled dynamically against the dataset's actual ratio range."""
    if df is None or df.empty:
        return FALLBACK_K
        
    atr_series = calculate_atr(df, period=atr_period)
    if atr_series.empty or len(atr_series) < 2:
        return FALLBACK_K
        
    # Read from the just past closed candle (iloc[-2]) to avoid live repainting bugs
    latest_atr = atr_series.iloc[-2] if len(atr_series) >= 2 else atr_series.iloc[-1]
    
    if pd.isna(latest_atr) or latest_atr == 0:
        return FALLBACK_K
        
    # Dynamically find the min and max from your actual history
    atr_scale_min = atr_series.min()
    atr_scale_max = atr_series.max()
    
    if atr_scale_max == atr_scale_min:
        return FALLBACK_K
        
    # Normalized position between 0.0 and 1.0 based entirely on actual data range
    norm_atr = (latest_atr - atr_scale_min) / (atr_scale_max - atr_scale_min)
    
    # Inverse exponential scaling logic
    k_dynamic = k_max - (k_max - k_min) * ((np.exp(norm_atr) - 1) / (np.e - 1))
    
    return round(k_dynamic, 2)

if __name__ == "__main__":
    try:
        df = fetch_yf_data()
    except Exception:
        df = None
        
    if df is not None and not df.empty and len(df) >= 2:
        atr_series = calculate_atr(df)
        dynamic_k = calculate_dynamic_k(df)
        
        # Pull the value of the just past closed candle (iloc[-2])
        val = atr_series.iloc[-2]
        
        if pd.isna(val) or val == 0:
            val = float(FALLBACK_ATR)
            dynamic_k = FALLBACK_K
            
        # Display the actual returned float value (rounded to 2 decimals since it's a ratio)
        left_text = f"ATR:{round(val, 2)}"
        right_text = f"K:{dynamic_k}"
        spacing = " " * max(TOTAL_WIDTH - len(left_text) - len(right_text), 1)
        print(left_text + spacing + right_text)
    else:
        left_text = f"ATR:{float(FALLBACK_ATR)}"
        right_text = f"K:{FALLBACK_K}"
        spacing = " " * max(TOTAL_WIDTH - len(left_text) - len(right_text), 1)
        print(left_text + spacing + right_text)


