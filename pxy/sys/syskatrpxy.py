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

# Production boundaries & safety fallbacks (Adjust these if your custom sum exceeds 12.0)
MIN_FLOOR = 6.0         # Locked: Absolute minimum ceiling/floor floor
MAX_CEILING = 12.0      # Locked: Absolute maximum ceiling
FALLBACK_ATR = 8.0      # Updated: Target safety anchor for errors/missing data

# Production scale anchors for dynamic K (Synchronized with ATR limits)
ATR_SCALE_MIN = 6.0
ATR_SCALE_MAX = 12.0
FALLBACK_K = 2.0

def calculate_atr(df: pd.DataFrame, period=ATR_PERIOD) -> pd.Series:
    """Calculates session-isolated custom 14-candle High-Low SUM with strict bounding and fallback."""
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
    
    # --- CUSTOM CALCULATION IMPLEMENTATION HERE ---
    # Pure High minus Low calculation (Direction and gaps are ignored)
    candle_range = high - low
    
    # Group rolling window SUM computations by session dates (Replaces rolling mean)
    atr = candle_range.groupby(date_groups, group_keys=False).apply(
        lambda x: x.rolling(window=period, min_periods=1).sum()
    )
    # -----------------------------------------------
    
    # Floor, Ceiling, and NaN safety mapping (Strictly bounds output between 6.0 and 12.0)
    return atr.apply(lambda x: float(FALLBACK_ATR) if pd.isna(x) or x == 0 else max(MIN_FLOOR, min(MAX_CEILING, float(x))))

def calculate_dynamic_k(df: pd.DataFrame, atr_period=ATR_PERIOD, k_min=K_MIN, k_max=K_MAX) -> float:
    """Calculates inverse exponential K value scaled safely against latest custom range sum."""
    if df is None or df.empty:
        return FALLBACK_K
        
    atr_series = calculate_atr(df, period=atr_period)
    if atr_series.empty:
        return FALLBACK_K
        
    latest_atr = atr_series.iloc[-1]
    
    # In the event of a data problem or a 0 value, return safe fallback baseline K
    if pd.isna(latest_atr) or latest_atr == 0:
        return FALLBACK_K
        
    # Strictly cap input ATR parameters between production anchors
    clamped_atr = max(ATR_SCALE_MIN, min(latest_atr, ATR_SCALE_MAX))
    
    # Normalized position between 0.0 and 1.0
    norm_atr = (clamped_atr - ATR_SCALE_MIN) / (ATR_SCALE_MAX - ATR_SCALE_MIN)
    
    # Inverse exponential scaling logic
    k_dynamic = k_max - (k_max - k_min) * ((np.exp(norm_atr) - 1) / (np.e - 1))
    
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
        if pd.isna(val) or val == 0 or len(atr_series) <= 1:
            val = float(FALLBACK_ATR)
            dynamic_k = FALLBACK_K
            
        atr_display = int(np.round(val))
        left_text = f"ATR:{atr_display}"
        right_text = f"K:{dynamic_k}"
        spacing = " " * max(TOTAL_WIDTH - len(left_text) - len(right_text), 1)
        print(left_text + spacing + right_text)
    else:
        # Synchronized static empty workspace layout
        left_text = f"ATR:{int(FALLBACK_ATR)}"
        right_text = f"K:{FALLBACK_K}"
        spacing = " " * max(TOTAL_WIDTH - len(left_text) - len(right_text), 1)
        print(left_text + spacing + right_text)

