# syskatrpxy.py
import pandas as pd
import numpy as np
import sys
from sysdtafpxy import fetch_yf_data
from syscnfgpxy import PARAMS
from colorama import Fore, Style, init

init(autoreset=True)

ATR_PERIOD = 14
K_MIN = 1
K_MAX = 3
TOTAL_WIDTH = 42

def clean_and_flatten_df(df: pd.DataFrame) -> pd.DataFrame:
    """Ensures historical data structures work across any single ticker format."""
    df_local = df.copy()
    
    # Secure time index parsing
    if not isinstance(df_local.index, pd.DatetimeIndex):
        df_local.index = pd.to_datetime(df_local.index)
    
    # Fix yfinance MultiIndex column structures if they exist
    if isinstance(df_local.columns, pd.MultiIndex):
        if 'Price' in df_local.columns.levels[0]:
            df_local = df_local.xs('Price', axis=1, level=0)  # Extract the core OHLCV matrix
        else:
            df_local.columns = df_local.columns.get_level_values(0) # Fallback flatten
            
    return df_local

def calculate_atr(df: pd.DataFrame, period=ATR_PERIOD) -> pd.Series:
    # Universal flattening step
    df_local = clean_and_flatten_df(df)
        
    high, low, close = df_local['High'], df_local['Low'], df_local['Close']
    prev_close = close.shift(1)
    
    # Calculate Standard True Range (Works for penny stocks up to $100k indices)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs()
    ], axis=1).max(axis=1)
    
    date_groups = df_local.index.date
    atr = tr.groupby(date_groups, group_keys=False).apply(
        lambda x: x.rolling(window=period, min_periods=1).mean()
    )
    
    return atr

def calculate_dynamic_k(df: pd.DataFrame, atr_period=ATR_PERIOD, k_min=K_MIN, k_max=K_MAX) -> float:
    atr_series = calculate_atr(df, period=atr_period)
    if atr_series.empty or atr_series.isna().all():
        return 2.0
        
    latest_atr = atr_series.iloc[-1]
    atr_subset = atr_series.iloc[-atr_period:].values if len(atr_series) >= atr_period else atr_series.values
    
    # Ignores NaNs safely if the index historical window has dead tracking zones
    atr_mean = np.nanmean(atr_subset) if len(atr_subset) > 0 else 0.0
    
    if pd.isna(latest_atr) or atr_mean == 0:
        return 2.0
        
    # Scale mathematical ratio into your bounds
    k_dynamic = k_min + (k_max - k_min) * (latest_atr / atr_mean)
    return round(max(min(k_dynamic, k_max), k_min), 2)

if __name__ == "__main__":
    # Accepts any target index passed from terminal execution
    target_index = sys.argv[1] if len(sys.argv) > 1 else "^GSPC"
    
    df = fetch_yf_data(target_index)
    if df is not None and not df.empty and len(df) >= 1:
        atr_series = calculate_atr(df)
        dynamic_k = calculate_dynamic_k(df)
        
        val = atr_series.iloc[-1] if not atr_series.empty else np.nan
        
        if not pd.isna(val):
            atr_display = str(int(np.round(val)))
        else:
            atr_display = "N/A"
        
        left_text = f"{target_index} ATR:{atr_display}"
        right_text = f"K:{dynamic_k}"
        spacing = " " * max(TOTAL_WIDTH - len(left_text) - len(right_text), 1)
        print(left_text + spacing + right_text)
    else:
        print(f"{target_index} ATR:N/A" + (" " * 25) + "K:2.0")
