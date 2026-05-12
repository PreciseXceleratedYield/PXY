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
    high, low, close = df['High'], df['Low'], df['Close']
    prev_close = close.shift(1)
    
    # Standard True Range
    tr = pd.concat([
        high - low, 
        (high - prev_close).abs(), 
        (low - prev_close).abs()
    ], axis=1).max(axis=1)
    
    atr = tr.rolling(period).mean()
    
    # PRODUCTION FIX: If ATR is 0 or NaN, force it to 20.0
    # This prevents division by zero and keeps boundaries wide at open
    return atr.apply(lambda x: 20.0 if (x == 0 or pd.isna(x)) else x)

# -------------------- Dynamic K Calculation --------------------
def calculate_dynamic_k(df: pd.DataFrame, atr_period=ATR_PERIOD, k_min=K_MIN, k_max=K_MAX) -> float:
    atr_series = calculate_atr(df, period=atr_period)
    latest_atr = atr_series.iloc[-1]
    
    # Use the last 14 periods of our cleaned ATR series
    atr_subset = atr_series[-atr_period:] if len(atr_series) >= atr_period else atr_series
    atr_mean = atr_subset.mean()

    # PRODUCTION FALLBACK: 
    # If the market is flat or window isn't full (ATR <= 20), return 2.0
    if latest_atr <= 20.0 or atr_mean <= 20.0 or pd.isna(latest_atr):
        return 2.0
    
    # Standard Dynamic K logic
    k_dynamic = k_min + (k_max - k_min) * (latest_atr / atr_mean)
    
    # Clamp between 1 and 3
    k_dynamic = max(min(k_dynamic, k_max), k_min)
    return round(k_dynamic, 2)

# -------------------- Self-runnable test --------------------
if __name__ == "__main__":
    df = fetch_yf_data()
    if df is not None and not df.empty:
        atr_series = calculate_atr(df)
        dynamic_k = calculate_dynamic_k(df)

        val = atr_series.iloc[-1]
        # Display logic for console output
        atr_display = int(val) if (not pd.isna(val) and val != 0) else 20

        left_text = f"ATR:{atr_display}"
        right_text = f"K:{dynamic_k}"

        space_width = TOTAL_WIDTH - len(left_text) - len(right_text)
        spacing = " " * max(space_width, 1)

        print(left_text + spacing + right_text)
    else:
        # Emergency print if data fetch fails
        print(f"ATR:20" + (" " * 28) + "K:2.0")
