# =============================================================================
# VOLATILITY ENGINE MODULE: syskatrpxy.py
# =============================================================================
import re
import pandas as pd
import numpy as np
from sysdtafpxy import fetch_yf_data
from syscnfgpxy import PARAMS
from colorama import Fore, Style, init

# 🎯 IMPORT UNTOUCHED SIGNAL ROUTER NATIVELY
from sysdptpxy import detect_pxy_flip_signal

# Initialize colorama terminal auto-reset formatting hooks
init(autoreset=True)

# Configuration Switches
USE_FIXED_ATR = False  # Set to False to use the dynamic matrix depth calculations
ATR_FIXED_VALUE = 9

ATR_PERIOD = 14
K_MIN = 1
K_MAX = 3
TOTAL_WIDTH = 42

def scale_atr_value_from_depth(past_str: str, ce_d: int, pe_d: int) -> float:
    """
    Extracts numbers from past_depth_str, ce_depth, and pe_depth.
    Sums them together and enforces ONLY a strict minimum of 5.0.
    Maximum can grow higher infinitely to any value.
    """
    try:
        # Extract integer digits cleanly from past_depth_str (e.g., 'CE4' -> 4)
        digits = re.findall(r'\d+', str(past_str))
        past_val_extracted = int(digits) if digits else 0
        
        # Aggregate depth sum matrix natively
        raw_depth_sum = past_val_extracted + int(ce_d) + int(pe_d)
        
        # 🎯 STEP 2: Enforce strict minimum boundary floor of 5.0
        # If the sum of depths is less than 5, it cannot go lower than 5.
        if raw_depth_sum < 5.0:
            return 5.0
            
        return float(raw_depth_sum)
    except Exception:
        return 5.0

def calculate_atr(df: pd.DataFrame, period=ATR_PERIOD) -> pd.Series:
    """Generates dynamic option volatility series derived from matrix color streak depths."""
    try:
        if USE_FIXED_ATR:
            if df is not None and not df.empty:
                return pd.Series(float(ATR_FIXED_VALUE), index=df.index)
            return pd.Series([float(ATR_FIXED_VALUE)])

        # 🎯 FETCH DEPTH PARAMETERS FROM YOUR UNCHANGED SIGNAL MODULE
        # Unpacks exactly 4 original values: signal, past_depth_str, ce_depth, pe_depth
        _, past_depth_str, ce_depth, pe_depth = detect_pxy_flip_signal(df=df)
        
        # Process depth integers through the bounded threshold calculator
        resolved_atr_value = scale_atr_value_from_depth(past_depth_str, ce_depth, pe_depth)

        # Populate structural series matching dataframe timeline layout
        if df is not None and not df.empty:
            return pd.Series(resolved_atr_value, index=df.index)
        return pd.Series([resolved_atr_value])

    except Exception:
        # Absolute structural fallback array tracking fallback to minimum baseline boundary
        if df is not None and not df.empty:
            return pd.Series(5.0, index=df.index)
        return pd.Series([5.0])

def calculate_dynamic_k(df: pd.DataFrame, atr_period=ATR_PERIOD, k_min=K_MIN, k_max=K_MAX) -> float:
    """Dynamically scales K factor based on deviation from historical average ATR data."""
    try:
        atr_series = calculate_atr(df, period=atr_period)
        if atr_series.empty:
            return 2.0
            
        latest_atr = atr_series.iloc[-1]
        atr_subset = atr_series.iloc[-atr_period:].values if len(atr_series) >= atr_period else atr_series.values
        
        # Fallback tracking parameters to safeguard mathematical division checks
        atr_mean = atr_subset.mean() if len(atr_subset) > 0 else 5.0
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
            
            val = atr_series.iloc[-1] if not atr_series.empty else 5.0
            atr_display = int(np.round(val)) if (not pd.isna(val) and val != 0) else 5
            
            left_text = f"ATR:{atr_display}"
            right_text = f"K:{dynamic_k}"
            spacing = " " * max(TOTAL_WIDTH - len(left_text) - len(right_text), 1)
            print(left_text + spacing + right_text)
        else:
            print("ATR:5" + (" " * 33) + "K:2.0")
    except Exception:
        print("ATR:5" + (" " * 33) + "K:2.0")

