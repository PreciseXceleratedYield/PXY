# sysstrndpxy.py
import sys
import numpy as np
import pandas as pd
import pytz
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

from syscnfgpxy import TIMEZONE

# Global Config 
DEBUG_MODE = True 
MA_TYPE = "TSMA"  
CHECK_CONFIRMED_ONLY = False  # ⚡ False = Process and trade the LIVE running candle (Index -1)

def calculate_supertrend(df: pd.DataFrame) -> pd.DataFrame: 
    """ 
    PXY® Engine Strategy Matrix.
    Forces full-day intraday context isolation dynamically from raw inputs.
    Calculates dynamic intraday resetting boundaries and isolates signals.
    """ 
    if df is None or df.empty:
        return pd.DataFrame()

    df = df.copy()

    # 1. 🎯 ISOLATE TRUE DAY-SPECIFIC DATA HISTORIES (Bypasses upstream fixed cutting)
    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index)
    
    tz_string = str(TIMEZONE)
    if df.index.tz is None:
        df = df.tz_localize('UTC').tz_convert(tz_string)
    else:
        df = df.tz_convert(tz_string)
        
    today_date = datetime.now(pytz.timezone(tz_string)).date()
    day_specific_df = df[df.index.date == today_date].copy()
    
    # Intraday context padding checkpoint for first morning bars
    if len(day_specific_df) >= 3:
        df = day_specific_df
    
    # 2. TIMELINE MANAGEMENT & INDEX ALIGNMENTS
    timestamps = df.index
    dates = timestamps.date
    n = len(df)
    
    src_o = df['Open'].to_numpy()
    src_h = df['High'].to_numpy()
    src_l = df['Low'].to_numpy()
    src_c = df['Close'].to_numpy()

    # 3. TOTAL INTRADAY SESSION STATISTICS MATH MATRIX
    sma_line   = np.zeros(n)
    tsma_line  = np.zeros(n)
    hh_session = np.zeros(n)
    ll_session = np.zeros(n)
    bar_count_session = np.zeros(n, dtype=int)

    current_count = 0
    sum_y = 0.0
    sum_x = 0.0
    sum_xx = 0.0
    sum_xy = 0.0
    curr_hh = np.nan
    curr_ll = np.nan

    for i in range(n):
        if i == 0 or dates[i] != dates[i-1]:
            current_count = 1
            sum_y  = src_c[i]
            sum_x  = 0.0
            sum_xx = 0.0
            sum_xy = 0.0
            curr_hh = src_h[i]
            curr_ll = src_l[i]
        else:
            current_count += 1
            idx = current_count - 1
            sum_y  += src_c[i]
            sum_x  += idx
            sum_xx += idx ** 2
            sum_xy += idx * src_c[i]
            curr_hh = max(curr_hh, src_h[i])
            curr_ll = min(curr_ll, src_l[i])

        bar_count_session[i] = current_count
        hh_session[i] = curr_hh
        ll_session[i] = curr_ll

        sma_line[i] = sum_y / current_count

        tsma_line[i] = src_c[i]
        if current_count > 1:
            num = (current_count * sum_xy) - (sum_x * sum_y)
            denom = (current_count * sum_xx) - (sum_x ** 2)
            if denom != 0:
                slope = num / denom
                current_idx = current_count - 1
                intercept = (sum_y - (slope * sum_x)) / current_count
                tsma_line[i] = (slope * current_idx) + intercept

    base_ma_line = sma_line if MA_TYPE.upper() == "SMA" else tsma_line

    df['pxy_st_line'] = (base_ma_line + hh_session + ll_session + src_c) / 4.0
    df['pxy_st_no_ll'] = (base_ma_line + hh_session + src_c) / 3.0 
    df['pxy_st_no_hh'] = (base_ma_line + ll_session + src_c) / 3.0 
    df['bar_count_session'] = bar_count_session
    df['src_c'] = src_c

    # 4. SPLIT LIFECYCLE COMPILATIONS: INDEPENDENT SIGNAL AND TREND ROUTERS
    st = df['pxy_st_line'].to_numpy()
    no_ll = df['pxy_st_no_ll'].to_numpy()
    no_hh = df['pxy_st_no_hh'].to_numpy()
    
    st_signal_history = [] 
    st_trend_history = []
    
    for i in range(n): 
        current_trend = "BULL" if src_c[i] >= st[i] else "BEAR"
        st_trend_history.append(current_trend)

        if bar_count_session[i] < 2: 
            st_signal_history.append("NONE") 
            continue 
            
        c0 = src_c[i]
        c1 = src_c[i-1]
        st0 = st[i]
        st1 = st[i-1]
        
        cross_buy  = (c0 > st0) and (c1 <= st1)
        cross_sell = (c0 < st0) and (c1 >= st1)
        
        force_buy  = (c0 > no_ll[i]) and (c1 <= no_ll[i-1])
        force_sell = (c0 < no_hh[i]) and (c1 >= no_hh[i-1])
        
        if force_buy:
            st_signal_history.append("FORCESELL")  
        elif force_sell:
            st_signal_history.append("FORCEBUY")   
        elif cross_buy:
            st_signal_history.append("CROSSBUY")   
        elif cross_sell:
            st_signal_history.append("CROSSSELL")  
        else:
            st_signal_history.append("NONE")

    df['st_signal_full'] = st_signal_history
    df['st_trend_full'] = st_trend_history
    
    # 🎯 DASHBOARD KEY BACKWARD COMPATIBILITY KEYS
    df['ST'] = df['pxy_st_line']
    df['ST_Trend'] = df['st_trend_full']
    return df

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
            print(f"Session Bar Intraday Count -> {calculated_df.at[calculated_df.index[idx], 'bar_count_session']}")
            print(f"Active Live Market SIGNAL  -> {active_signal}")
            print(f"Active Live Market TREND   -> {active_trend}\n")
            
        return active_signal, active_trend
        
    except Exception as e:
        if DEBUG_MODE:
            print(f"PXY Master Output Routing Module Exception: {e}")
        return "NONE", "NONE"

if __name__ == "__main__":
    from sysdtafpxy import fetch_yf_data
    
    print("\n[PXY STRND ENGINE] Standalone Live Stream Listener Initiated.")
    print(f"Configuration -> CHECK_CONFIRMED_ONLY: {CHECK_CONFIRMED_ONLY} | MA_TYPE: {MA_TYPE}")
    print("--------------------------------------------------")
    
    try:
        print("Polling latest session data from sysdtafpxy...")
        live_df = fetch_yf_data()
        
        if live_df is not None and not live_df.empty:
            print(f"Data Successfully Retrieved. Analyzing {len(live_df)} matrix intervals.")
            signal, trend = get_signal(live_df)
            
            print("==================================================")
            print(f"⚡ LIVE STREAM OUTPUT -> Signal: {signal} | Trend: {trend}")
            print("==================================================\n")
        else:
            print("❌ Error: Upstream module returned an empty or invalid DataFrame frame.")
            
    except Exception as e:
        print(f"❌ Critical Connection Exception Hit: {e}")



