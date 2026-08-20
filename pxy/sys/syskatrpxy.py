# =============================================================================
# VOLATILITY ENGINE MODULE: syskatrpxy.py
# =============================================================================
import re
import pandas as pd
import numpy as np
from sysdtafpxy import fetch_yf_data
from syscnfgpxy import PARAMS
from colorama import Fore, Style, init

# 🎯 IMPORT UNTOUCHED SIGNAL ROUTER NATIVELY (Returns exactly 4 values)
from sysdptpxy import detect_pxy_flip_signal

# Initialize colorama terminal auto-reset formatting hooks
init(autoreset=True)

# Configuration Switches
USE_FIXED_ATR = False  
ATR_FIXED_VALUE = 9
TOTAL_WIDTH = 42

def safe_int_convert(val, fallback=1) -> int:
    """Prevents calculation crashes from empty fields, None, or invalid text types."""
    if val is None:
        return fallback
    try:
        # Convert to string, strip whitespace, and parse clean decimals
        clean_str = str(val).replace(',', '').strip()
        if not clean_str:
            return fallback
        return int(round(float(clean_str)))
    except (ValueError, TypeError):
        return fallback

def scale_atr_value_from_depth(past_str: str, ce_d: int, pe_d: int) -> int:
    """
    Extracts numbers from past_depth_str, ce_depth, and pe_depth.
    Sums all three numbers together and enforces ONLY a strict minimum of 5.
    Maximum can grow higher infinitely to any value.
    """
    try:
        # Clean string extraction for past depth digit sequences (e.g. 'PE4' -> ['4'])
        digits = re.findall(r'\d+', str(past_str))
        past_val_extracted = int(digits[0]) if digits else 0
        
        # 🎯 SECURE DATA CONVERSIONS: Prevents type errors from interrupting loop steps
        c_depth_clean = safe_int_convert(ce_d, fallback=1)
        p_depth_clean = safe_int_convert(pe_d, fallback=1)
        
        # 🎯 ATR MATH: Pure sum of all 3 depth metrics
        raw_depth_sum = c_depth_clean + p_depth_clean #past_val_extracted + c_depth_clean + p_depth_clean
        
        # Enforce strict minimum floor boundary of 5
        if raw_depth_sum < 5:
            return 5
            
        return int(raw_depth_sum)
    except Exception:
        return 5

def calculate_atr_from_snapshot(past_depth_str: str, ce_depth: int, pe_depth: int) -> int:
    """Calculates ATR directly using pre-fetched snapshot variables to prevent timing lags."""
    return scale_atr_value_from_depth(past_depth_str, ce_depth, pe_depth)

def calculate_k_from_snapshot(ce_depth: int, pe_depth: int) -> int:
    """Calculates K directly using pre-fetched snapshot variables to prevent timing lags."""
    return safe_int_convert(ce_depth, fallback=1) + safe_int_convert(pe_depth, fallback=1)

# --- BACKWARD COMPATIBILITY METHODS FOR EXTERNAL SCRIPT LINKS ---
def calculate_atr(df: pd.DataFrame) -> pd.Series:
    try:
        _, past_str, ce_d, pe_d = detect_pxy_flip_signal(df=df)
        val = scale_atr_value_from_depth(past_str, ce_d, pe_d)
        return pd.Series(float(val), index=df.index) if df is not None and not df.empty else pd.Series([float(val)])
    except Exception:
        return pd.Series(5.0, index=df.index) if df is not None and not df.empty else pd.Series([5.0])

def calculate_dynamic_k(df: pd.DataFrame) -> int:
    try:
        _, _, ce_d, pe_d = detect_pxy_flip_signal(df=df)
        return safe_int_convert(ce_d, fallback=1) + safe_int_convert(pe_d, fallback=1)
    except Exception:
        return 2

# =============================================================================
# UNIFIED SNAPSHOTTING EXECUTION BLOCK
# =============================================================================
if __name__ == "__main__":
    try:
        df = fetch_yf_data()
        if df is not None and not df.empty and len(df) >= 1:
            
            # 🎯 PULL DATA ONCE: Synchronizes calculation pools instantly
            _, past_depth_str, ce_depth, pe_depth = detect_pxy_flip_signal(df=df)
            
            final_atr = calculate_atr_from_snapshot(past_depth_str, ce_depth, pe_depth)
            final_k = calculate_k_from_snapshot(ce_depth, pe_depth)
            
            # Display perfectly synchronized metrics within terminal frames
            left_text = f"ATR:{final_atr}"
            right_text = f"K:{final_k}"
            spacing = " " * max(TOTAL_WIDTH - len(left_text) - len(right_text), 1)
            print(left_text + spacing + right_text)
        else:
            print("ATR:5" + (" " * 33) + "K:2")
    except Exception:
        print("ATR:5" + (" " * 33) + "K:2")


