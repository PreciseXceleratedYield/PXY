# =============================================================================
# VOLATILITY ENGINE MODULE: syskatrpxy.py
# =============================================================================
import pandas as pd
import numpy as np
from sysdtafpxy import fetch_yf_data
from syscnfgpxy import PARAMS
from colorama import Fore, Style, init

# Initialize colorama terminal auto-reset formatting hooks
init(autoreset=True)

# Configuration Switches
USE_FIXED_ATR = False  # Set to False to use the dynamic ATR calculations
ATR_FIXED_VALUE = 9

ATR_PERIOD = 14
K_MIN = 1
K_MAX = 3
TOTAL_WIDTH = 42

def scale_atr_value(val: float) -> float:
    """
    Scales ATR: Takes the raw ATR value directly (no division).
    Enforces a strict minimum floor barrier of 3.0 and a maximum ceiling of 9.0.
    """
    if pd.isna(val) or val <= 0:
        return 3.0
        
    # Convert incoming value safely to float
    raw_val = float(val)
    
    # 🎯 APPLY BOUNDED CAPPING ENGINE (MIN = 3, MAX = 9)
    if raw_val < 3.0:
        return 3.0
    if raw_val > 9.0:
        return 9.0
        
    return raw_val

def calculate_atr(df: pd.DataFrame, period=ATR_PERIOD) -> pd.Series:
    """Calculates smoothed rolling ATR groups clustered by active trading dates."""
    try:
        if USE_FIXED_ATR:
            if df is not None and not df.empty:
                return pd.Series(float(ATR_FIXED_VALUE), index=df.index)
            return pd.Series([float(ATR_FIXED_VALUE)])

        working_df = df.copy()
        
        # Secure time index parsing to clear layout alignment anomalies
        if not isinstance(working_df.index, pd.DatetimeIndex):
            working_df.index = pd.to_datetime(working_df.index)
        
        high, low, close = working_df['High'], working_df['Low'], working_df['Close']
        prev_close = close.shift(1)
        
        # Calculate Standard True Range matrix boundaries
        tr = pd.concat([
            high - low,
            (high - prev_close).abs(),
            (low - prev_close).abs()
        ], axis=1).max(axis=1)
        
        # Group rolling window mean computations cleanly by session dates
        date_groups = working_df.index.date
        atr = tr.groupby(date_groups, group_keys=False).apply(
            lambda x: x.rolling(window=period, min_periods=1).mean()
        )
        
        # Apply the simplified raw bounded limits [3.0, 9.0]
        return atr.apply(scale_atr_value)
    except Exception:
        # Absolute structural fallback array tracking fallback to standard baseline point
        if df is not None and not df.empty:
            return pd.Series(7.0, index=df.index)
        return pd.Series([7.0])

def calculate_dynamic_k(df: pd.DataFrame, atr_period=ATR_PERIOD, k_min=K_MIN, k_max=K_MAX) -> float:
    """Dynamically scales K factor based on deviation from historical average ATR data."""
    try:
        atr_series = calculate_atr(df, period=atr_period)
        if atr_series.empty:
            return 2.0
            
        latest_atr = atr_series.iloc[-1]
        atr_subset = atr_series.iloc[-atr_period:].values if len(atr_series) >= atr_period else atr_series.values
        
        # Fallback tracking parameters to safeguard mathematical inversion checks
        atr_mean = atr_subset.mean() if len(atr_subset) > 0 else 7.0
        if pd.isna(latest_atr) or atr_mean == 0:
            return 2.0
            
        k_dynamic = k_min + (k_max - k_min) * (latest_atr / atr_mean)
        return round(max(min(k_dynamic, k_max), k_min), 2)
    except Exception:
        return 2.0

if __name__ == "__main__":
    try:
        df = fetch_yf_data()
        if df is not None and not df.empty and len(df) >= 1:
            atr_series = calculate_atr(df)
            dynamic_k = calculate_dynamic_k(df)
            
            val = atr_series.iloc[-1] if not atr_series.empty else 7.0
            atr_display = int(np.round(val)) if (not pd.isna(val) and val != 0) else 7
            
            left_text = f"ATR:{atr_display}"
            right_text = f"K:{dynamic_k}"
            spacing = " " * max(TOTAL_WIDTH - len(left_text) - len(right_text), 1)
            print(left_text + spacing + right_text)
        else:
            print("ATR:7" + (" " * 33) + "K:2.0")
    except Exception:
        print("ATR:7" + (" " * 33) + "K:2.0")
