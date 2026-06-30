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

# Production boundaries & safety fallbacks for standard ATR
MIN_FLOOR = 6.0         
MAX_CEILING = 12.0      
FALLBACK_ATR = 8.0      

FALLBACK_K = 2.0

def calculate_atr(df: pd.DataFrame, period=ATR_PERIOD) -> pd.Series:
    """Calculates session-isolated rolling ATR with strict 6.0-12.0 bounding and 8.0 fallback."""
    if df is None or df.empty or len(df) < 1:
        return pd.Series([float(FALLBACK_ATR)])
    
    df_local = df.copy()
    
    if not isinstance(df_local.index, pd.DatetimeIndex):
        df_local.index = pd.to_datetime(df_local.index)
        
    df_local.columns = [col.capitalize() for col in df_local.columns]
    required_cols = ['High', 'Low', 'Close']
    
    if not all(col in df_local.columns for col in required_cols):
        return pd.Series([float(FALLBACK_ATR)], index=df_local.index if not df_local.empty else None)
        
    high, low, close = df_local['High'], df_local['Low'], df_local['Close']
    prev_close = close.shift(1)
    
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs()
    ], axis=1).max(axis=1)
    
    date_groups = df_local.index.date
    atr = tr.groupby(date_groups, group_keys=False).apply(
        lambda x: x.rolling(window=period, min_periods=1).mean()
    )
    
    return atr.apply(lambda x: float(FALLBACK_ATR) if pd.isna(x) or x == 0 else max(MIN_FLOOR, min(MAX_CEILING, float(x))))

def calculate_dynamic_k(df: pd.DataFrame, atr_period=ATR_PERIOD, k_min=K_MIN, k_max=K_MAX) -> float:
    """Calculates inverse exponential K value driven by the custom past closed candle ratio."""
    if df is None or df.empty or len(df) < 2:
        return FALLBACK_K
        
    df_local = df.copy()
    if not isinstance(df_local.index, pd.DatetimeIndex):
        df_local.index = pd.to_datetime(df_local.index)
    df_local.columns = [col.capitalize() for col in df_local.columns]
    
    high, low = df_local['High'], df_local['Low']
    candle_range = high - low
    
    date_groups = df_local.index.date
    rolling_sum = candle_range.groupby(date_groups, group_keys=False).apply(
        lambda x: x.rolling(window=atr_period, min_periods=1).sum()
    )
    
    custom_ratio_series = (candle_range * 14) / rolling_sum.replace(0, np.nan)
    latest_ratio = custom_ratio_series.iloc[-2]
    
    if pd.isna(latest_ratio) or latest_ratio == 0:
        return FALLBACK_K
        
    ratio_min = custom_ratio_series.min()
    ratio_max = custom_ratio_series.max()
    
    if ratio_max == ratio_min:
        return FALLBACK_K
        
    norm_atr = (latest_ratio - ratio_min) / (ratio_max - ratio_min)
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
        
        val = atr_series.iloc[-1] if not atr_series.empty else float(FALLBACK_ATR)
        
        if pd.isna(val) or val == 0 or len(atr_series) <= 1:
            val = float(FALLBACK_ATR)
            dynamic_k = FALLBACK_K
            
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


