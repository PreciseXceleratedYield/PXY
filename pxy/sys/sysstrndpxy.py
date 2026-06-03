# sysstrndpxy.py
import numpy as np
import pandas as pd

# Global Config 
DEBUG_MODE = True 
MA_TYPE = "TSMA"  
CHECK_CONFIRMED_ONLY = False  # ⚡ False = Process and trade the LIVE running candle (Index -1)

def calculate_supertrend(df: pd.DataFrame) -> pd.DataFrame: 
    """ 
    PXY® Engine Strategy Matrix.
    Processes dynamic session lookback indicators and separates Actionable Trigger 
    Signals from continuous Foundational Directional Trends.
    """ 
    if df is None or df.empty:
        return pd.DataFrame()

    df = df.copy()
    
    # 1. TIMEZONE & TIMELINE EXTRACTION CONSTRAINTS
    if isinstance(df.index, pd.DatetimeIndex):
        timestamps = df.index
    else:
        timestamps = pd.to_datetime(df['Timestamp'] if 'Timestamp' in df.columns else df.index)
    dates = timestamps.date

    n = len(df)
    ha_o = np.zeros(n)
    
    raw_open  = df['Open'].to_numpy()
    raw_high  = df['High'].to_numpy()
    raw_low   = df['Low'].to_numpy()
    raw_close = df['Close'].to_numpy()

    # Isolated daily Heikin-Ashi generator loops
    for i in range(n):
        ha_c_i = (raw_open[i] + raw_high[i] + raw_low[i] + raw_close[i]) / 4.0
        if i == 0 or dates[i] != dates[i-1]:
            ha_o[i] = (raw_open[i] + raw_close[i]) / 2.0
        else:
            ha_o[i] = (ha_o[i-1] + ha_c_i) / 2.0

    ha_c = (raw_open + raw_high + raw_low + raw_close) / 4.0
    ha_h = np.maximum(raw_high, np.maximum(ha_o, ha_c))
    ha_l = np.minimum(raw_low, np.maximum(ha_o, ha_c))

    oc2 = (raw_open + raw_close) / 2.0
    raw_c1 = np.copy(raw_close)
    raw_c1[1:] = raw_close[:-1]

    # Explicit Mode 5 assignments compiled natively inside the matrix framework
    src_o = (raw_open + ha_o + oc2 + raw_c1) / 4.0
    src_h = (raw_high + ha_h + oc2 + raw_close) / 4.0
    src_l = (raw_low + ha_l + oc2 + raw_c1) / 4.0
    src_c = (raw_close + ha_c + oc2 + raw_close) / 4.0

    # 2. TOTAL INTRADAY SESSION STATISTICS MATH MATRIX
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
            # Morning boundary initialization routine resets calculations to data index 0
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

        # Resetting Session SMA
        sma_line[i] = sum_y / current_count

        # Resetting Session Linear Regression Endpoint (TSMA)
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

    # Channel Line Output Arrays
    df['pxy_st_line'] = (base_ma_line + hh_session + ll_session + src_c) / 4.0
    df['pxy_st_no_ll'] = (base_ma_line + hh_session + src_c) / 3.0 # Upper Band
    df['pxy_st_no_hh'] = (base_ma_line + ll_session + src_c) / 3.0 # Lower Band
    df['bar_count_session'] = bar_count_session
    df['src_c'] = src_c

    # 3. SPLIT LIFECYCLE COMPILATIONS: INDEPENDENT SIGNAL AND TREND ROUTERS
    st = df['pxy_st_line'].to_numpy()
    no_ll = df['pxy_st_no_ll'].to_numpy()
    no_hh = df['pxy_st_no_hh'].to_numpy()
    
    st_signal_history = [] 
    st_trend_history = []
    
    for i in range(n): 
        # Foundational continuous trend state tracker: Price Up = BULL | Price Down = BEAR
        current_trend = "BULL" if src_c[i] >= st[i] else "BEAR"
        st_trend_history.append(current_trend)

        if bar_count_session[i] < 2: 
            st_signal_history.append("NONE") 
            continue 
            
        c0 = src_c[i]
        c1 = src_c[i-1]
        st0 = st[i]
        st1 = st[i-1]
        
        # Line cross configurations
        cross_buy  = (c0 > st0) and (c1 <= st1)
        cross_sell = (c0 < st0) and (c1 >= st1)
        
        # Outer exhaustion thresholds
        force_buy  = (c0 > no_ll[i]) and (c1 <= no_ll[i-1])
        force_sell = (c0 < no_hh[i]) and (c1 >= no_hh[i-1])
        
        # Enforce Priority Conditional Structure
        if force_buy:
            st_signal_history.append("FORCESELL")  
        elif force_sell:
            st_signal_history.append("FORCEBUY")   
        elif cross_buy:
            st_signal_history.append("CROSSBUY")   
        elif cross_sell:
            st_signal_history.append("CROSSSELL")  
        else:
            st_signal_history.append("NONE") # Registers NONE if no crossover rules hit

    df['st_signal_full'] = st_signal_history
    df['st_trend_full'] = st_trend_history
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
        
        # Route index window selection based on configuration switch parameters
        if CHECK_CONFIRMED_ONLY:
            idx = n - 2  # 🔒 Complete Closed Bar (Non-Reprinting)
        else:
            idx = n - 1  # ⚡ Live Running Forming Candle (Real-Time Tracker)

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

# Standalone execution validation loop
if __name__ == "__main__":
    # 🎯 FIXED: Corrected module function import name mapping to match sysdthapxy.py exactly
    from sysdthapxy import fetch_yf_data
    
    print("\n[PXY STRND ENGINE] Standalone Live Stream Listener Initiated.")
    print(f"Configuration -> CHECK_CONFIRMED_ONLY: {CHECK_CONFIRMED_ONLY} | MA_TYPE: {MA_TYPE}")
    print("--------------------------------------------------")
    
    try:
        print("Polling latest day-specific session data from sysdthapxy...")
        live_df = fetch_yf_data()
        
        if live_df is not None and not live_df.empty:
            print(f"Data Successfully Retrieved. Analyzing {len(live_df)} session matrix intervals.")
            signal, trend = get_signal(live_df)
            
            print("==================================================")
            print(f"⚡ LIVE STREAM OUTPUT -> Signal: {signal} | Trend: {trend}")
            print("==================================================\n")
        else:
            print("❌ Error: Upstream module returned an empty or invalid DataFrame frame.")
            
    except Exception as e:
        print(f"❌ Critical Connection Exception Hit: {e}")


