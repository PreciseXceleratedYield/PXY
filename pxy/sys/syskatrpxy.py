import sys
import os
import re
import pandas as pd
import numpy as np
from sysdtafpxy import fetch_yf_data
from syscnfgpxy import PARAMS
from colorama import Fore, Style, init

from sysdptpxy import detect_pxy_flip_signal
from syspwerpxy import get_ce_pe_power

init(autoreset=True)

# 🎯 MULTI-MODE NUMERIC CONFIGURATION MATRIX
# 1 = Static, 2 = Standard ATR (14), 3 = Dynamic
ATR_MODE = 2 
ATR_STATIC_VALUE = 7
TOTAL_WIDTH = 40

def safe_int_convert(val, fallback=1) -> int:
    if val is None:
        return fallback
    try:
        clean_str = str(val).replace(',', '').strip()
        if not clean_str:
            return fallback
        return int(round(float(clean_str)))
    except (ValueError, TypeError):
        return fallback

def calculate_true_14_atr(df: pd.DataFrame) -> float:
    """Computes genuine standard 14-period Average True Range math."""
    try:
        if df is None or df.empty or len(df) < 15:
            return 14.0
        
        df_clean = df.copy()
        df_clean.columns = [c.lower() for c in df_clean.columns]
        
        high = df_clean['high']
        low = df_clean['low']
        close_prev = df_clean['close'].shift(1)
        
        tr1 = high - low
        tr2 = (high - close_prev).abs()
        tr3 = (low - close_prev).abs()
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        # Standard Wilders smoothing execution sequence over 14 intervals
        atr_series = tr.ewm(alpha=1/14, adjust=False).mean()
        val = atr_series.iloc[-1]
        
        return float(val) if not np.isnan(val) else 14.0
    except Exception:
        return 14.0

def scale_atr_value_from_depth(past_str: str, ce_d: int, pe_d: int, ce_p: int = 1, pe_p: int = 1) -> int:
    try:
        c_depth = safe_int_convert(ce_d)
        p_depth = safe_int_convert(pe_d)
        c_power = safe_int_convert(ce_p)
        p_power = safe_int_convert(pe_p)
        
        raw_sum = c_depth + p_depth + c_power + p_power
        return int(raw_sum) if raw_sum >= 5 else 5
    except Exception:
        return 5

# --- BACKWARD COMPATIBILITY LINKERS FOR OUTSIDE POOLS ---
def calculate_atr(df: pd.DataFrame) -> pd.Series:
    try:
        if ATR_MODE == 1:
            val = float(ATR_STATIC_VALUE)
        elif ATR_MODE == 2:
            val = calculate_true_14_atr(df)
        else:
            _, past_str, ce_d, pe_d = detect_pxy_flip_signal(df=df)
            _, ce_p, pe_p = get_ce_pe_power(df)
            val = float(scale_atr_value_from_depth(past_str, ce_d, pe_d, ce_p, pe_p))
            
        return pd.Series(val, index=df.index) if df is not None and not df.empty else pd.Series([val])
    except Exception:
        fb = 14.0 if ATR_MODE == 2 else (float(ATR_STATIC_VALUE) if ATR_MODE == 1 else 5.0)
        return pd.Series(fb, index=df.index) if df is not None and not df.empty else pd.Series([fb])

def calculate_dynamic_k(df: pd.DataFrame) -> int:
    try:
        _, _, ce_d, pe_d = detect_pxy_flip_signal(df=df)
        return safe_int_convert(ce_d) + safe_int_convert(pe_d)
    except Exception:
        return 2


if __name__ == "__main__":
    try:
        df = fetch_yf_data()
        final_atr = 14
        final_k = 2
        
        if df is not None and not df.empty:
            if ATR_MODE == 1:
                final_atr = int(ATR_STATIC_VALUE)
            elif ATR_MODE == 2:
                final_atr = int(round(calculate_true_14_atr(df)))
            else:
                _, past_depth_str, ce_depth, pe_depth = detect_pxy_flip_signal(df=df)
                _, ce_power, pe_power = get_ce_pe_power(df)
                final_atr = scale_atr_value_from_depth(past_depth_str, ce_depth, pe_depth, ce_power, pe_power)
                
            _, _, ce_depth, pe_depth = detect_pxy_flip_signal(df=df)
            final_k = safe_int_convert(ce_depth) + safe_int_convert(pe_depth)

        l_txt = f"ATR:{final_atr}"
        r_txt = f"K:{final_k}"
        spc = " " * max(TOTAL_WIDTH - len(l_txt) - len(r_txt), 1)
        print(l_txt + spc + r_txt)
    except Exception:
        default_atr = 14 if ATR_MODE == 2 else (ATR_STATIC_VALUE if ATR_MODE == 1 else 5)
        l_txt = f"ATR:{default_atr}"
        r_txt = "K:2"
        spc = " " * max(TOTAL_WIDTH - len(l_txt) - len(r_txt), 1)
        print(l_txt + spc + r_txt)
