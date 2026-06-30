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

# Only keeping basic fallback constants if data is missing completely
FALLBACK_ATR = 50.0      # Adjusted higher to better reflect a typical 14-candle sum baseline
FALLBACK_K = 2.0

def calculate_atr(df: pd.DataFrame, period=ATR_PERIOD) -> pd.Series:
    """Calculates session-isolated custom 14-candle High-Low SUM with NO hard limits."""
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
    
    # Pure High minus Low calculation (Direction and gaps are ignored)
    candle_range = high - low
    
    # Define date groups from index for session grouping
    date_groups = df_local.index.date
    
    # Group rolling window SUM computations by session dates
    atr = candle_range.groupby(date_groups, group_keys=False).apply(
        lambda x: x.rolling(window=period, min_periods=1).sum()
    )
    
    # Only map NaNs/zeros to fallback; no more floor or ceiling clamping
    return atr.apply(lambda x: float(FALLBACK_ATR) if pd.isna(x) or x == 0 else float(x))

def calculate_dynamic_k(df: pd.DataFrame, atr_period=ATR_PERIOD, k_min=K_MIN, k_max=K_MAX) -> float:
    """Calculates inverse exponential K value scaled dynamically against the dataset's actual min/max."""
    if df is None or df.empty:
        return FALLBACK_K
        
    atr_series = calculate_atr(df, period=atr_period)
    if atr_series.empty:
        return FALLBACK_K
        
    latest_atr = atr_series.iloc[-1]
    
    if pd.isna(latest_atr) or latest_atr == 0:
        return FALLBACK_K
        
    # Dynamically find the min and max from your actual history instead of hardcoded 6.0 and 12.0
    atr_scale_min = atr_series.min()
    atr_scale_max = atr_series.max()
    
    # Avoid division by zero if all values are identical
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
        
    if df is not None and not df.empty and len(df) >= 1:
        atr_series = calculate_atr(df)
        dynamic_k = calculate_dynamic_k(df)
        
        val = atr_series.iloc[-1] if not atr_series.empty else float(FALLBACK_ATR)
        
        if pd.isna(val) or val == 0 or len(atr_series) <= 1:
            val = float(FALLBACK_ATR)
            dynamic_k = FALLBACK_K
            
        # Display the real un-clamped raw number
        atr_display = int(np.round(val))
        left_text = f"ATR:{atr_display}"
        right_text = f"K:{dynamic_k}"
        spacing = " " * max(TOTAL_WIDTH - len(left_text) - len(right_text), 1)
        print(left_text + spacing + right_text)
    else:
        left_text = f"ATR:{int(FALLBACK_ATR)}"
        right_text = f"K:{FALLBACK_K}"
        spacing = " " * max(TOTAL_WIDTH - len(left_text) - len(right_text), 1)
        print(left_text + spacing + right_text)


