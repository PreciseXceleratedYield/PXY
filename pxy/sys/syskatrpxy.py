# syskatrpxy.py
import pandas as pd
from sysdtafpxy import fetch_yf_data
from syscnfgpxy import PARAMS  # only for TICKER
from colorama import Fore, Style, init

# Initialize Colorama
init(autoreset=True)

# -------------------- Hardcoded constants --------------------
ATR_PERIOD = 14
K_MIN = 1
K_MAX = 3
TOTAL_WIDTH = 42

# -------------------- ATR Calculation --------------------
def calculate_atr(df: pd.DataFrame, period=ATR_PERIOD) -> pd.Series:
    high = df['High']
    low = df['Low']
    close = df['Close']
    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs()
    ], axis=1).max(axis=1)
    atr = tr.rolling(period).mean()
    return atr

# -------------------- Dynamic K Calculation --------------------
def calculate_dynamic_k(df: pd.DataFrame, atr_period=ATR_PERIOD, k_min=K_MIN, k_max=K_MAX) -> float:
    atr = calculate_atr(df, period=atr_period)
    latest_atr = atr.iloc[-1]
    atr_mean = atr[-atr_period:].mean() if len(atr) >= atr_period else atr.mean()
    if atr_mean == 0:
        return k_min
    k_dynamic = k_min + (k_max - k_min) * (latest_atr / atr_mean)
    k_dynamic = max(min(k_dynamic, k_max), k_min)
    return round(k_dynamic, 2)

# -------------------- Self-runnable test --------------------
if __name__ == "__main__":
    df = fetch_yf_data()
    atr_series = calculate_atr(df)
    dynamic_k = calculate_dynamic_k(df)

    # Convert latest ATR to integer for display
    atr_int = int(atr_series.iloc[-1]) if not pd.isna(atr_series.iloc[-1]) else "-"

    # Labels and values
    left_text = f"ATR:{atr_int}"
    right_text = f"K:{dynamic_k}"

    # Compute spacing for total width = 42
    space_width = TOTAL_WIDTH - len(left_text) - len(right_text)
    if space_width < 0:
        space_width = 1
    spacing = " " * space_width

    # Print single line (no color coding needed)
    print(left_text + spacing + right_text)
