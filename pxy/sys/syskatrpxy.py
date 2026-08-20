# =============================================================================
# VOLATILITY ENGINE MODULE: syskatrpxy.py
# =============================================================================
import re
import pandas as pd
import numpy as np
from sysdtafpxy import fetch_yf_data
from syscnfgpxy import PARAMS
from colorama import Fore, Style, init

# 🎯 IMPORT UNTOUCHED SIGNAL ROUTER NATIVELY (Returns 4 values)
from syskatrpxy import detect_pxy_flip_signal

# Initialize colorama terminal auto-reset formatting hooks
init(autoreset=True)

# Configuration Switches
USE_FIXED_ATR = False  # Set to False to use the dynamic matrix depth calculations
ATR_FIXED_VALUE = 9
TOTAL_WIDTH = 42

def scale_atr_value_from_depth(past_str: str, ce_d: int, pe_d: int) -> int:
    """
    Extracts numbers from past_depth_str, ce_depth, and pe_depth.
    Sums all three numbers together and enforces ONLY a strict minimum of 5.
    """
    try:
        # Extract integer digits cleanly from past_depth_str (e.g., 'CE4' -> 4)
        digits = re.findall(r'\d+', str(past_str))
        past_val_extracted = int(digits) if digits else 0
        
        # 🎯 ATR MATH: Pure sum of all 3 depth metrics
        raw_depth_sum = past_val_extracted + int(ce_d) + int(pe_d)
        
        # Enforce strict minimum floor boundary of 5
        if raw_depth_sum < 5:
            return 5
            
        return int(raw_depth_sum)
    except Exception:
        return 5

def calculate_atr(df: pd.DataFrame) -> pd.Series:
    """Generates dynamic option volatility series derived from matrix color streak depths."""
    try:
        if USE_FIXED_ATR:
            if df is not None and not df.empty:
                return pd.Series(float(ATR_FIXED_VALUE), index=df.index)
            return pd.Series([float(ATR_FIXED_VALUE)])

        # 🎯 FETCH DEPTH PARAMETERS FROM YOUR UNCHANGED SIGNAL MODULE
        _, past_depth_str, ce_depth, pe_depth = detect_pxy_flip_signal(df=df)
        
        # Process depth integers through the pure sum calculator
        resolved_atr_value = scale_atr_value_from_depth(past_depth_str, ce_depth, pe_depth)

        # Populate structural series matching dataframe timeline layout
        if df is not None and not df.empty:
            return pd.Series(float(resolved_atr_value), index=df.index)
        return pd.Series([float(resolved_atr_value)])

    except Exception:
        if df is not None and not df.empty:
            return pd.Series(5.0, index=df.index)
        return pd.Series([5.0])

def calculate_dynamic_k(df: pd.DataFrame) -> int:
    """
    🎯 K METHOD: Calculates K as a direct pure sum of 2 fields (pe_depth + ce_depth).
    """
    try:
        # Fetch fresh raw parameters from unchanged script module
        _, _, ce_depth, pe_depth = detect_pxy_flip_signal(df=df)
        
        # 🎯 K MATH: Pure sum of the 2 active metrics
        k_calculated = int(pe_depth) + int(ce_depth)
        return int(k_calculated)
    except Exception:
        return 2

if __name__ == "__main__":
    try:
        df = fetch_yf_data()
        if df is not None and not df.empty and len(df) >= 1:
            atr_series = calculate_atr(df)
            dynamic_k = calculate_dynamic_k(df)
            
            val = atr_series.iloc[-1] if not atr_series.empty else 5.0
            atr_display = int(np.round(val))
            
            # Displays both parameters as pure integers inside the dashboard panel layout frame
            left_text = f"ATR:{atr_display}"
            right_text = f"K:{int(dynamic_k)}"
            spacing = " " * max(TOTAL_WIDTH - len(left_text) - len(right_text), 1)
            print(left_text + spacing + right_text)
        else:
            print("ATR:5" + (" " * 33) + "K:2")
    except Exception:
        print("ATR:5" + (" " * 33) + "K:2")

