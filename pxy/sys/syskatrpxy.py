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

# 🎯 IMPORT EXTERNAL POWER ENGINE NATIVELY
from syspwerpxy import get_ce_pe_power

# Initialize colorama terminal auto-reset formatting hooks
init(autoreset=True)

# Configuration Switches
USE_FIXED_ATR = True  
ATR_FIXED_VALUE = 7
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

def scale_atr_value_from_depth(past_str: str, ce_d: int, pe_d: int, ce_p: int = 1, pe_p: int = 1) -> int:
    """
    Extracts numbers from past_depth_str, ce_depth, and pe_depth.
    🎯 ATR MATH: Sum of CE Depth + PE Depth + CE Power + PE Power.
    Enforces ONLY a strict minimum of 5. Maximum can grow higher infinitely.
    """
    # 🎯 FIX: Check configuration flag first
    if USE_FIXED_ATR:
        return ATR_FIXED_VALUE

    try:
        # Clean string extraction for past depth digit sequences (e.g. 'PE4' -> ['4'])
        digits = re.findall(r'\d+', str(past_str))
        past_val_extracted = int(digits[0]) if digits else 0
        
        # 🎯 SECURE DATA CONVERSIONS: Prevents type errors from interrupting loop steps
        c_depth_clean = safe_int_convert(ce_d, fallback=1)
        p_depth_clean = safe_int_convert(pe_d, fallback=1)
        c_power_clean = safe_int_convert(ce_p, fallback=1)
        p_power_clean = safe_int_convert(pe_p, fallback=1)
        
        # 🎯 NEW ATR FORMULA FORMULATION
        raw_depth_sum = c_depth_clean + p_depth_clean + c_power_clean + p_power_clean
        
        # Enforce strict minimum floor boundary of 5
        if raw_depth_sum < 5:
            return 5
            
        return int(raw_depth_sum)
    except Exception:
        return 5

def calculate_atr_from_snapshot(past_depth_str: str, ce_depth: int, pe_depth: int, ce_power: int, pe_power: int) -> int:
    """Calculates ATR directly using pre-fetched snapshot variables to prevent timing lags."""
    if USE_FIXED_ATR:
        return ATR_FIXED_VALUE
    return scale_atr_value_from_depth(past_depth_str, ce_depth, pe_depth, ce_power, pe_power)

def calculate_k_from_snapshot(ce_depth: int, pe_depth: int) -> int:
    """Calculates K directly using pre-fetched snapshot variables to prevent timing lags."""
    return safe_int_convert(ce_depth, fallback=1) + safe_int_convert(pe_depth, fallback=1)

# --- BACKWARD COMPATIBILITY METHODS FOR EXTERNAL SCRIPT LINKS ---
def calculate_atr(df: pd.DataFrame) -> pd.Series:
    try:
        if USE_FIXED_ATR:
            val = ATR_FIXED_VALUE
        else:
            _, past_str, ce_d, pe_d = detect_pxy_flip_signal(df=df)
            _, ce_p, pe_p = get_ce_pe_power(df)
            val = scale_atr_value_from_depth(past_str, ce_d, pe_d, ce_p, pe_p)
        return pd.Series(float(val), index=df.index) if df is not None and not df.empty else pd.Series([float(val)])
    except Exception:
        fallback_val = float(ATR_FIXED_VALUE) if USE_FIXED_ATR else 5.0
        return pd.Series(fallback_val, index=df.index) if df is not None and not df.empty else pd.Series([fallback_val])

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
            _, ce_power, pe_power = get_ce_pe_power(df)
            
            final_atr = calculate_atr_from_snapshot(past_depth_str, ce_depth, pe_depth, ce_power, pe_power)
            final_k = calculate_k_from_snapshot(ce_depth, pe_depth)
            
            # Display perfectly synchronized metrics within terminal frames
            left_text = f"ATR:{final_atr}"
            right_text = f"K:{final_k}"
            spacing = " " * max(TOTAL_WIDTH - len(left_text) - len(right_text), 1)
            print(left_text + spacing + right_text)
        else:
            fallback_atr = ATR_FIXED_VALUE if USE_FIXED_ATR else 5
            print(f"ATR:{fallback_atr}" + (" " * (34 - len(str(fallback_atr)))) + "K:2")
    except Exception:
        fallback_atr = ATR_FIXED_VALUE if USE_FIXED_ATR else 5
        print(f"ATR:{fallback_atr}" + (" " * (34 - len(str(fallback_atr)))) + "K:2")
