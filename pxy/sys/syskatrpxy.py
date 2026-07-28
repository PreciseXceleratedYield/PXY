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

def calculate_atr(df: pd.DataFrame, period=ATR_PERIOD) -> pd.Series:
    try:
        df_local = df.copy()
        
        # Secure time index parsing
        if not isinstance(df_local.index, pd.DatetimeIndex):
            df_local.index = pd.to_datetime(df_local.index)
            
        high, low, close = df_local['High'], df_local['Low'], df_local['Close']
        prev_close = close.shift(1)
        
        # Calculate Standard True Range
        tr = pd.concat([
            high - low,
            (high - prev_close).abs(),
            (low - prev_close).abs()
        ], axis=1).max(axis=1)
        
        # Group rolling window mean computations by session dates
        date_groups = df_local.index.date
        atr = tr.groupby(date_groups, group_keys=False).apply(
            lambda x: x.rolling(window=period, min_periods=1).mean()
        )
        
        # Error / Empty state fallback altered strictly to 7.0
        return atr.apply(lambda x: 7.0 if (x <= 0 or pd.isna(x)) else float(x))
    except Exception:
        # Absolute fallback return array structure populated with 7.0
        if df is not None and not df.empty:
            return pd.Series(7.0, index=df.index)
        return pd.Series([7.0])

def calculate_dynamic_k(df: pd.DataFrame, atr_period=ATR_PERIOD, k_min=K_MIN, k_max=K_MAX) -> float:
    try:
        atr_series = calculate_atr(df, period=atr_period)
        if atr_series.empty:
            return 2.0
            
        latest_atr = atr_series.iloc[-1]
        atr_subset = atr_series.iloc[-atr_period:].values if len(atr_series) >= atr_period else atr_series.values
        
        # Fallback to 7.0 instead of epsilon to protect calculation bounds
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
            print(f"ATR:7" + (" " * 33) + "K:2.0")
    except Exception:
        print(f"ATR:7" + (" " * 33) + "K:2.0")

