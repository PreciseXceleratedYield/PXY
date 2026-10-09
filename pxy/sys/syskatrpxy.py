import sys
import os
import re
import pandas as pd
import numpy as np
from sysdtafpxy import fetch_yf_data
from syscnfgpxy import (
    SYSCNFGPXY_TIMEZONE,
    SYSKATRPXY_ATR_MODE,
    SYSKATRPXY_ATR_STATIC_VALUE,
    SYSKATRPXY_DEPTH_ATR_MINIMUM,
    SYSKATRPXY_TRUE_ATR_MAX,
    SYSKATRPXY_TRUE_ATR_FALLBACK_VALUE,
    SYSKATRPXY_TRUE_ATR_MIN_ROWS,
    SYSKATRPXY_TRUE_ATR_PERIOD,
)
from colorama import Fore, Style, init

from sysdptpxy import detect_pxy_flip_signal
from syspwerpxy import get_ce_pe_power

init(autoreset=True)

# ATR modes: 1 = static, 2 = session true-range ATR, 3 = dynamic depth/power.
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

def calculate_true_atr_series(df: pd.DataFrame) -> pd.Series:
    """Return a per-candle session ATR, expanding to 14 bars then rolling."""
    try:
        if df is None or df.empty:
            return pd.Series(dtype=float, name="atr")
        
        df_clean = df.copy()
        df_clean.columns = [c.lower() for c in df_clean.columns]

        if not isinstance(df_clean.index, pd.DatetimeIndex):
            timestamps = pd.to_datetime(df_clean.index)
            if timestamps.tz is None:
                timestamps = timestamps.tz_localize("UTC")
            local_timestamps = timestamps.tz_convert(str(SYSCNFGPXY_TIMEZONE))
            df_clean.index = local_timestamps
        elif df_clean.index.tz is None:
            df_clean.index = df_clean.index.tz_localize("UTC").tz_convert(
                str(SYSCNFGPXY_TIMEZONE)
            )
        else:
            df_clean.index = df_clean.index.tz_convert(str(SYSCNFGPXY_TIMEZONE))

        high = df_clean['high']
        low = df_clean['low']
        close_prev = df_clean['close'].shift(1)
        
        tr1 = high - low
        tr2 = (high - close_prev).abs()
        tr3 = (low - close_prev).abs()
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

        atr_values = np.full(len(df_clean), SYSKATRPXY_TRUE_ATR_FALLBACK_VALUE)
        local_dates = df_clean.index.date
        session_start = pd.Timestamp("09:16").time()
        for session in pd.unique(local_dates):
            positions = np.flatnonzero(
                (local_dates == session)
                & (df_clean.index.time >= session_start)
            )
            if len(positions) < SYSKATRPXY_TRUE_ATR_MIN_ROWS:
                continue
            session_tr = tr.iloc[positions]
            if df_clean.index[positions[0]].time() == session_start:
                session_tr.iloc[0] = tr1.iloc[positions[0]]
            session_atr = session_tr.rolling(
                window=SYSKATRPXY_TRUE_ATR_PERIOD,
                min_periods=1,
            ).mean()
            capped = session_atr.clip(upper=SYSKATRPXY_TRUE_ATR_MAX)
            atr_values[positions] = capped.fillna(
                SYSKATRPXY_TRUE_ATR_FALLBACK_VALUE
            ).to_numpy()
        return pd.Series(atr_values, index=df.index, name="atr")
    except Exception:
        if df is None or df.empty:
            return pd.Series(dtype=float, name="atr")
        return pd.Series(
            SYSKATRPXY_TRUE_ATR_FALLBACK_VALUE,
            index=df.index,
            name="atr",
        )


def calculate_true_atr(df: pd.DataFrame) -> float:
    """Return the latest value from the session-based true-range ATR series."""
    atr_series = calculate_true_atr_series(df)
    if atr_series.empty:
        return SYSKATRPXY_TRUE_ATR_FALLBACK_VALUE
    return float(atr_series.iloc[-1])

def scale_atr_value_from_depth(past_str: str, ce_d: int, pe_d: int, ce_p: int = 1, pe_p: int = 1) -> int:
    try:
        c_depth = safe_int_convert(ce_d)
        p_depth = safe_int_convert(pe_d)
        c_power = safe_int_convert(ce_p)
        p_power = safe_int_convert(pe_p)
        
        raw_sum = c_depth + p_depth + c_power + p_power
        return max(int(raw_sum), SYSKATRPXY_DEPTH_ATR_MINIMUM)
    except Exception:
        return SYSKATRPXY_DEPTH_ATR_MINIMUM


def _configured_atr_fallback() -> float:
    if SYSKATRPXY_ATR_MODE == 1:
        return float(SYSKATRPXY_ATR_STATIC_VALUE)
    if SYSKATRPXY_ATR_MODE == 2:
        return SYSKATRPXY_TRUE_ATR_FALLBACK_VALUE
    return float(SYSKATRPXY_DEPTH_ATR_MINIMUM)

# --- BACKWARD COMPATIBILITY LINKERS FOR OUTSIDE POOLS ---
def calculate_atr(df: pd.DataFrame) -> pd.Series:
    try:
        if SYSKATRPXY_ATR_MODE == 1:
            val = float(SYSKATRPXY_ATR_STATIC_VALUE)
        elif SYSKATRPXY_ATR_MODE == 2:
            if df is None or df.empty:
                return pd.Series([calculate_true_atr(df)])
            return calculate_true_atr_series(df)
        else:
            _, past_str, ce_d, pe_d = detect_pxy_flip_signal(df=df)
            _, ce_p, pe_p = get_ce_pe_power(df)
            val = float(scale_atr_value_from_depth(past_str, ce_d, pe_d, ce_p, pe_p))
            
        return pd.Series(val, index=df.index) if df is not None and not df.empty else pd.Series([val])
    except Exception:
        fb = _configured_atr_fallback()
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
        final_atr = _configured_atr_fallback()
        final_k = 2
        
        if df is not None and not df.empty:
            if SYSKATRPXY_ATR_MODE == 1:
                final_atr = int(SYSKATRPXY_ATR_STATIC_VALUE)
            elif SYSKATRPXY_ATR_MODE == 2:
                final_atr = int(round(calculate_true_atr(df)))
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
        default_atr = _configured_atr_fallback()
        l_txt = f"ATR:{default_atr}"
        r_txt = "K:2"
        spc = " " * max(TOTAL_WIDTH - len(l_txt) - len(r_txt), 1)
        print(l_txt + spc + r_txt)
