# sys/exe/dynentrypxy.py
import pandas as pd
from colorama import Fore, Style, init

# Initialize colorama for colored terminal output
init(autoreset=True)

# Global tracking structures
printed_sides = set()

def f(x, d=0.0):
    """Safely cast input to float, return default if casting fails or value <= 0."""
    try:
        val = float(x)
        return val if val > 0 else d
    except Exception:
        return d

def i(x, d=0):
    """Safely cast input to integer, return default if casting fails."""
    try:
        return int(float(x))
    except Exception:
        return d

def dynamic_entry(row):
    """Returns the raw entry price from row dictionary entries with no tracking variables."""
    try:
        return round(float(row.get("buy_prc", 0)), 2)
    except Exception:
        return 0.0

def target_price(row):
    """Calculates target price based strictly on matrix parameters and signal direction."""
    global printed_sides
    try:
        # 1. Extract base values and powers needed for printing and logic
        atr_val = f(row.get("atr"), 6.0)
        ce_power = f(row.get("ce_power"), 1.0)
        pe_power = f(row.get("pe_power"), 1.0)
        
        ce_disp = int(ce_power) if float(ce_power).is_integer() else ce_power
        pe_disp = int(pe_power) if float(pe_power).is_integer() else pe_power
        atr_disp = int(atr_val) if float(atr_val).is_integer() else round(atr_val, 2)

        # 2. Print status line exactly once per refresh cycle using unique data snapshot
        print_key = f"{atr_disp}_{ce_disp}_{pe_disp}"
        if print_key not in printed_sides:
            raw_display_len = len(f" {atr_disp} BUY : {ce_disp}% SELL: {pe_disp}%") + 6
            spaces_needed = max(0, (40 - raw_display_len) // 2)
            padding = " " * spaces_needed
            print(f"{padding}↕️ {atr_disp} {Fore.GREEN}🟢 BUY : {ce_disp}% {Fore.RED}🔴 SELL: {pe_disp}%")
            printed_sides.add(print_key)

        # 3. Entry data health check (Handles explicit zero payloads cleanly)
        entry_prc = f(row.get("pxy_entry") if row.get("pxy_entry") is not None else row.get("buy_prc"))
        if entry_prc <= 0:
            return 0.0

        # 4. Context extractors
        symbol = str(row.get("symbol", "unknown")).upper()
        active_exit = str(row.get("exit", "NONE")).upper().strip()
        is_ce = "CE" in symbol
        is_pe = "PE" in symbol
        
        if not is_ce and not is_pe:
            return round(entry_prc, 2)

        # 5. Extract Option Matrix parameters
        hce_d = f(row.get("hkin_ce_depth"), 1.0)
        hpe_d = f(row.get("hkin_pe_depth"), 1.0)
        ce_p = f(row.get("ce_power"), 1.0)
        pe_p = f(row.get("pe_power"), 1.0)
        
        target_pct = 0.0

        # 6. Core execution logic evaluating directional signals
        if is_ce:
            if active_exit in ["SELL", "BEAR"]:
                target_pct = atr_val / 2
            else:
                target_pct = atr_val
        elif is_pe:
            if active_exit in ["BUY", "BULL"]:
                target_pct = atr_val / 2
            else:
                target_pct = atr_val

        # 7. Final mathematical target projection calculation
        calculated_target = entry_prc * (1 + (target_pct / 100.0))
        return round(calculated_target, 2)

    except Exception as e:
        print(f"{Fore.RED}Error in target_price engine: {e}{Style.RESET_ALL}")
        return 0.0
# sysstrndpxy.py
import sys
import numpy as np
import pandas as pd
import pytz
import json
import os
from datetime import datetime
import warnings

# Silence future warning constraints completely
warnings.simplefilter(action='ignore', category=FutureWarning)

# ---- Pure Production Naming Alignment Imports ----
from sysdtafpxy import fetch_yf_data
from syskatrpxy import calculate_atr, calculate_dynamic_k
from syscnfgpxy import TIMEZONE, TICKER

# Global Config 
DEBUG_MODE = False 
CHECK_CONFIRMED_ONLY = False  # ⚡ False = Target live running index (-1) for real-time changes

def calculate_supertrend(df: pd.DataFrame) -> pd.DataFrame: 
    """ 
    Blended Pipeline Engine.
    Calculates SMA 42 and a 7-period, 7.0 Factor Supertrend.
    Averages both engines into a hybrid tracking line.
    Returns: BULL, BEAR, BUY, or SELL based on the blended trend regime.
    """ 
    try:
        raw_df = fetch_yf_data(period="3d", interval="1m") 
        if not raw_df.empty:
            df = raw_df
    except Exception as e:
        if DEBUG_MODE:
            print(f"Warning: Shared pipeline download fallback active | {e}")

    df = df.copy()

    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index)
    
    tz_string = str(TIMEZONE)
    if df.index.tz is None:
        df = df.tz_localize('UTC').tz_convert(tz_string)
    else:
        df = df.tz_convert(tz_string)
        
    n = len(df)
    if n == 0:
        return df

    # EXTRACT UPSTREAM PRE-CALCULATED MODE 0 OHLC DATA ARRAYS
    src_open  = df['Open'].to_numpy()
    src_high  = df['High'].to_numpy()
    src_low   = df['Low'].to_numpy()
    src_close = df['Close'].to_numpy()

    # ===============================================================================
    # 📈 COMPUTE SMA 42 COMPONENT
    # ===============================================================================
    sma42_series = df['Close'].rolling(window=42).mean()
    sma42_series = sma42_series.bfill()
    sma42_arr = sma42_series.to_numpy()

    # ===============================================================================
    # 📡 COMPUTE 7:7 SUPERTREND COMPONENT
    # ===============================================================================
    st7_length = 7
    st7_mult   = 7.0
    
    hl2_baseline = (src_high + src_low) / 2.0
    
    tr_mod = src_high - src_low
    for i in range(1, n):
        t1 = src_high[i] - src_low[i]
        t2 = abs(src_high[i] - src_close[i-1])
        t3 = abs(src_low[i] - src_close[i-1])
        tr_mod[i] = max(t1, t2, t3)
        
    tr_series = pd.Series(tr_mod)
    atr7_series = tr_series.rolling(window=st7_length).mean()
    atr7_series = atr7_series.bfill()
    atr7_arr = atr7_series.to_numpy()

    basic_upper = hl2_baseline + (atr7_arr * st7_mult)
    basic_lower = hl2_baseline - (atr7_arr * st7_mult)

    final_upper     = np.zeros(n)
    final_lower     = np.zeros(n)
    trend_direction = np.ones(n, dtype=int)

    final_upper = basic_upper.copy()
    final_lower = basic_lower.copy()
    trend_direction = np.where(src_close >= hl2_baseline, 1, -1)

    for i in range(1, n):
        if (basic_upper[i] < final_upper[i-1]) or (src_close[i-1] > final_upper[i-1]):
            final_upper[i] = basic_upper[i]
        else:
            final_upper[i] = final_upper[i-1]

        if (basic_lower[i] > final_lower[i-1]) or (src_close[i-1] < final_lower[i-1]):
            final_lower[i] = basic_lower[i]
        else:
            final_lower[i] = final_lower[i-1]

        prev_dir = trend_direction[i-1]
        if prev_dir == 1 and src_close[i] < final_lower[i]:
            trend_direction[i] = -1
        elif prev_dir == -1 and src_close[i] > final_upper[i]:
            trend_direction[i] = 1
        else:
            trend_direction[i] = prev_dir

    st7_line = np.where(trend_direction == 1, final_lower, final_upper)

    # ===============================================================================
    # 🎛️ BLENDED HYBRID MATRICES (SMA42 + SUPERTREND7:7) / 2
    # ===============================================================================
    blended_line = (sma42_arr + st7_line) / 2.0
    df['pxy_sma_line'] = blended_line

    blended_direction = np.ones(n, dtype=int)
    blended_direction = np.where(src_close >= blended_line, 1, -1)

    # ===============================================================================
    # 🛠️ UNIFIED SINGLE ASYMMETRIC TREND STATE GENERATION
    # ===============================================================================
    sma_trend_history = []
    
    for i in range(n): 
        raw_sma_regime = "BULL" if blended_direction[i] == 1 else "BEAR"

        if i < 1: 
            sma_trend_history.append(raw_sma_regime)
            continue 

        sma_cross_buy  = (blended_direction[i] == 1)  and (blended_direction[i-1] == -1)
        sma_cross_sell = (blended_direction[i] == -1) and (blended_direction[i-1] == 1)

        if sma_cross_buy:
            sma_trend_history.append("BUY")
        elif sma_cross_sell:
            sma_trend_history.append("SELL")
        else:
            sma_trend_history.append(raw_sma_regime)

    df['sma_trend_full'] = sma_trend_history
    df['src_c'] = src_close
    
    # Dashboard Mappings
    df['pxy_st_line'] = df['pxy_sma_line']
    df['st_trend_full'] = df['sma_trend_full']
    df['ST'] = df['pxy_sma_line']
    df['ST_Trend'] = df['sma_trend_full']
    df['P_Master'] = df['src_c']
    
    try:
        df['shared_atr'] = calculate_atr(df)
    except Exception:
        df['shared_atr'] = 12.0
    
    return df

def export_supertrend_json(df: pd.DataFrame = None, output_file="../web/webchrtpxy.json"):
    """Dumps EVERY single candle printed straight to the JSON file."""
    if df is None or df.empty:
        dummy_df = pd.DataFrame()
        df = calculate_supertrend(dummy_df)
    
    if df is None or df.empty:
        return None

    output = []
    for idx, row in df.iterrows():
        output.append({
            "time": str(idx),
            "close": float(row["Close"]),
            "p_master": float(row["Close"]),  
            "st": float(row["pxy_sma_line"]),           
            "st_trend": str(row["sma_trend_full"]),
            "sma_line": float(row["pxy_sma_line"]),
            "sma_trend": str(row["sma_trend_full"])
        })

    os.makedirs(os.path.dirname(output_file), exist_ok=True) if os.path.dirname(output_file) else None
    with open(output_file, "w") as f:
        json.dump(output, f, indent=2)
    return output

def get_signal(df: pd.DataFrame) -> str:
    """Unpacks and returns the sole pipeline state cleanly for routing preferences."""
    if df is None or df.empty:
        df = pd.DataFrame()
        
    try:
        calculated_df = calculate_supertrend(df)
        n = len(calculated_df)
        if n == 0:
            return "NONE"
        
        idx = n - 2 if CHECK_CONFIRMED_ONLY else n - 1  
        active_sma_state = str(calculated_df.at[calculated_df.index[idx], 'sma_trend_full']).upper().strip()
        
        latest_atr_val = int(calculated_df.at[calculated_df.index[idx], 'shared_atr'])
        latest_k_val = calculate_dynamic_k(calculated_df)

        if DEBUG_MODE:
            print(f"--- PXY SINGLE-PIPE MONITOR SUMMARY ---")
            print(f"Target Row Lookup Index   -> {idx}")
            print(f"Active Trend state        -> {active_sma_state}")
            
        return active_sma_state
    except Exception as e:
        if DEBUG_MODE:
            print(f"Critical execution fault in system signal unpacker: {e}")
        return "NONE"

# ===============================================================================
# 🚀 DIRECT LIVE PRODUCTION EXECUTION BLOCK
# ===============================================================================
if __name__ == "__main__":
    print("--- STARTING LIVE PXY BLENDED SMA/ST MONITOR ENGINE ---")
    
    live_df = pd.DataFrame()
    processed_df = calculate_supertrend(live_df)
    
    if processed_df is not None and not processed_df.empty:
        idx_pos = -2 if CHECK_CONFIRMED_ONLY else -1
        target_index = processed_df.index[idx_pos]
        
        live_time = target_index.strftime('%Y-%m-%d %H:%M:%S %Z')
        live_close = float(processed_df.at[target_index, 'Close'])
        live_line = float(processed_df.at[target_index, 'pxy_sma_line'])
        live_state = str(processed_df.at[target_index, 'sma_trend_full'])
        
        print(f"Target Row Index Position -> {idx_pos} ({'CLOSED BAR' if CHECK_CONFIRMED_ONLY else 'LIVE TICK'})")
        print(f"Timestamp   : {live_time}")
        print(f"Close Price : {live_close:.2f}")
        print(f"Engine Line : {live_line:.2f}")
        print(f"Trend State : {live_state}")
        
        export_supertrend_json(processed_df)
    else:
        print("CRITICAL: Engine calculation aborted | Upstream data stream arrived empty.")

