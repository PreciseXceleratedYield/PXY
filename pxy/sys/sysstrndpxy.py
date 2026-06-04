# sysstrndpxy.py
import sys
import numpy as np
import pandas as pd
import pytz
import yfinance as yf
import json
import os
from datetime import datetime

# 🛠️ GLOBAL PROJECT HOTPATCH: Overrides config objects at initialization to prevent yfinance/pytz crashes
try:
    import syscnfgpxy
    if hasattr(syscnfgpxy, 'TIMEZONE'):
        if hasattr(syscnfgpxy.TIMEZONE, 'zone'):
            syscnfgpxy.TIMEZONE = str(syscnfgpxy.TIMEZONE.zone)
        else:
            syscnfgpxy.TIMEZONE = str(syscnfgpxy.TIMEZONE)
except Exception:
    pass

from syscnfgpxy import TIMEZONE, TICKER

# Global Config 
DEBUG_MODE = True 
MA_TYPE = "TSMA"  
CHECK_CONFIRMED_ONLY = False  # ⚡ False = Process and trade the LIVE running candle (Index -1)

def calculate_supertrend(df: pd.DataFrame) -> pd.DataFrame: 
    """ 
    PXY® Engine Strategy Matrix.
    Bypasses truncated upstream slices by fetching a fresh full-day session history.
    Calculates single-line HA TSMA 380 + Live Price / 2 and isolates signal crossovers.
    """ 
    # 🎯 OVERRIDE: Fetch a clean historical multi-day block straight from yfinance 
    try:
        ticker_obj = yf.Ticker(TICKER)
        raw_df = ticker_obj.history(period="5d", interval="1m")
        if not raw_df.empty:
            df = raw_df
    except Exception as e:
        if DEBUG_MODE:
            print(f"Warning: Independent yFinance download fallback active | {e}")

    df = df.copy()

    # 1. TIMELINE ISOLATION: FILTER FOR TODAY'S SESSION CANDLES ONLY (09:15 AM to 15:40 PM)
    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index)
    
    tz_string = str(TIMEZONE)
    if df.index.tz is None:
        df = df.tz_localize('UTC').tz_convert(tz_string)
    else:
        df = df.tz_convert(tz_string)
        
    today_date = datetime.now(pytz.timezone(tz_string)).date()
    day_specific_df = df[df.index.date == today_date].copy()
    
    # If today's session is active, commit to it entirely
    if not day_specific_df.empty:
        df = day_specific_df
    
    n = len(df)
    if n == 0:
        return df

    # 2. CONVERT STANDARD CANDLES TO PURE HEIKIN-ASHI ARRAYS
    src_o = df['Open'].to_numpy()
    src_h = df['High'].to_numpy()
    src_l = df['Low'].to_numpy()
    src_c = df['Close'].to_numpy()

    ha_open  = np.zeros(n)
    ha_high  = np.zeros(n)
    ha_low   = np.zeros(n)
    ha_close = np.zeros(n)

    # Initialize first candle
    ha_open[0]  = (src_o[0] + src_c[0]) / 2.0
    ha_close[0] = (src_o[0] + src_h[0] + src_l[0] + src_c[0]) / 4.0
    ha_high[0]  = max(src_h[0], ha_open[0], ha_close[0])
    ha_low[0]   = min(src_l[0], ha_open[0], ha_close[0])

    # Calculate rolling historical Heikin-Ashi matrix
    for i in range(1, n):
        ha_close[i] = (src_o[i] + src_h[i] + src_l[i] + src_c[i]) / 4.0
        ha_open[i]  = (ha_open[i-1] + ha_close[i-1]) / 2.0
        ha_high[i]  = max(src_h[i], ha_open[i], ha_close[i])
        ha_low[i]   = min(src_l[i], ha_open[i], ha_close[i])

    # Define live price source: (HA High + HA Low) / 2
    ha_live_source = (ha_high + ha_low) / 2.0

    # 3. TSMA 380 ROLLING REGRESSION CALCULATION
    tsma_380 = np.zeros(n)
    window = 380

    # X-coordinates for the regression window: [0, 1, 2, ... 379]
    x_reg = np.arange(window)
    sum_x = np.sum(x_reg)
    sum_xx = np.sum(x_reg ** 2)
    denom = (window * sum_xx) - (sum_x ** 2)

    for i in range(n):
        if i < window - 1:
            # Fallback initialization using dynamic window for early session minutes
            curr_win = i + 1
            if curr_win <= 1:
                tsma_380[i] = ha_live_source[i]
            else:
                x_sub = np.arange(curr_win)
                y_sub = ha_live_source[0:i+1]
                slope, intercept = np.polyfit(x_sub, y_sub, 1)
                tsma_380[i] = (slope * (curr_win - 1)) + intercept
        else:
            # Fast matrix tracking for closed window periods
            y_sub = ha_live_source[i - window + 1 : i + 1]
            sum_y = np.sum(y_sub)
            sum_xy = np.sum(x_reg * y_sub)
            
            num = (window * sum_xy) - (sum_x * sum_y)
            slope = num / denom
            intercept = (sum_y - (slope * sum_x)) / window
            tsma_380[i] = (slope * (window - 1)) + intercept

    # 4. SINGLE BLENDED LINE ASSIGNMENT: (TSMA 380 + HA Live Source) / 2
    blended_line = (tsma_380 + ha_live_source) / 2.0

    df['pxy_st_line'] = blended_line
    df['bar_count_session'] = np.arange(1, n + 1)
    df['src_c'] = ha_close  # Swapped with Heikin-Ashi output close

    # 5. SIGNAL PIPELINE INVERSION USING SINGLE MASTER LINE RULES
    st_signal_history = [] 
    st_trend_history = []
    
    for i in range(n): 
        current_trend = "BULL" if ha_close[i] >= blended_line[i] else "BEAR"
        st_trend_history.append(current_trend)

        if i < 1: 
            st_signal_history.append("NONE") 
            continue 
            
        c0 = ha_close[i]
        c1 = ha_close[i-1]
        line0 = blended_line[i]
        line1 = blended_line[i-1]
        
        cross_buy  = (c0 > line0) and (c1 <= line1)
        cross_sell = (c0 < line0) and (c1 >= line1)
        
        if cross_buy:
            st_signal_history.append("CROSSBUY")   
        elif cross_sell:
            st_signal_history.append("CROSSSELL")  
        else:
            st_signal_history.append("NONE")

    df['st_signal_full'] = st_signal_history
    df['st_trend_full'] = st_trend_history
    
    # 🎯 DASHBOARD BACKWARD-COMPATIBILITY KEYS
    df['ST'] = df['pxy_st_line']
    df['ST_Trend'] = df['st_trend_full']
    return df

def export_supertrend_json(output_file="../syschrtpxy.json"):
    """
    🎯 ABSORBED CHART EXPORT (FULL DAY SPECIFIC)
    Dumps EVERY single candle printed since today's opening bell straight to the JSON file.
    """
    dummy_df = pd.DataFrame()
    df = calculate_supertrend(dummy_df)
    
    if df is None or df.empty:
        print("No data processed for charting.")
        return None

    output = []
    for idx, row in df.iterrows():
        output.append({
            "time": str(idx),
            "close": float(row["Close"]),
            "p_master": float(row["Close"]),  
            "st": float(row["ST"]),           
            "st_trend": str(row["ST_Trend"])  
        })

    os.makedirs(os.path.dirname(output_file), exist_ok=True) if os.path.dirname(output_file) else None
    with open(output_file, "w") as f:
        json.dump(output, f, indent=2)

    return output

def get_signal(df: pd.DataFrame) -> tuple:
    """
    Direct array slice endpoint collector matching checkout preferences.
    """
    if df is None or df.empty:
        return "NONE", "NONE"
        
    try:
        calculated_df = calculate_supertrend(df)
        n = len(calculated_df)
        
        if CHECK_CONFIRMED_ONLY:
            idx = n - 2  
        else:
            idx = n - 1  

        active_signal = str(calculated_df.at[calculated_df.index[idx], 'st_signal_full']).upper().strip()
        active_trend  = str(calculated_df.at[calculated_df.index[idx], 'st_trend_full']).upper().strip()
        
        if DEBUG_MODE:
            print(f"--- PXY STRATEGY EVALUATION SUMMARY ---")
            print(f"Target Row Lookup Index   -> {idx}")
            print(f"Active Live Market SIGNAL  -> {active_signal}")
            print(f"Active Live Market TREND   -> {active_trend}\n")
            
        return active_signal, active_trend
        
    except Exception as e:
        if DEBUG_MODE:
            print(f"PXY Master Output Routing Module Exception: {e}")
        return "NONE", "NONE"

# Standalone execution validation loop
if __name__ == "__main__":
    print("\n[PXY STRND ENGINE] Standalone Live Stream Listener Initiated.")
    print(f"Configuration -> CHECK_CONFIRMED_ONLY: {CHECK_CONFIRMED_ONLY} | MA_TYPE: {MA_TYPE}")
    print("--------------------------------------------------")
    
    # Run test run validation using fallback data block
    dummy = pd.DataFrame()
    signal, trend = get_signal(dummy)
    export_supertrend_json()





