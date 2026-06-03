# sysstrndpxy.py
import numpy as np
import pandas as pd

# Global Config 
DEBUG_MODE = True 
MA_TYPE = "TSMA"  
CHECK_CONFIRMED_ONLY = False  # ⚡ False = Process and trade the LIVE running candle (Index -1)

def calculate_sma_42(series: pd.Series) -> np.ndarray: 
    """ Replaced by Session-Specific SMA inside the main matrix driver """
    pass

def calculate_tsma_42(series: pd.Series) -> np.ndarray: 
    """ Replaced by Session-Specific Linear Regression inside the main matrix driver """
    pass

def calculate_supertrend(df: pd.DataFrame) -> pd.DataFrame: 
    """ 
    PXY® Engine: Re-mapped to your exact original architecture.
    Calculates Mode 5, runs Intraday Session memory resets, and compiles historical trend strings.
    """ 
    if df is None or df.empty:
        return pd.DataFrame()

    df = df.copy()
    
    # 1. ISOLATED MODE 5 MATRIX GENERATOR (COMPOSITE BLEND)
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

    src_o = (raw_open + ha_o + oc2 + raw_c1) / 4.0
    src_h = (raw_high + ha_h + oc2 + raw_close) / 4.0
    src_l = (raw_low + ha_l + oc2 + raw_c1) / 4.0
    src_c = (raw_close + ha_c + oc2 + raw_close) / 4.0

    # 2. DYNAMIC INTRADAY SESSION MEMORY MANAGEMENT
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

        # Session-Specific SMA
        sma_line[i] = sum_y / current_count

        # Session-Specific TSMA Linear Regression Line Endpoint
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

    # 3. CHANNEL STRUCTURAL ASSIGNMENTS
    df['pxy_st_line'] = (base_ma_line + hh_session + ll_session + src_c) / 4.0
    df['pxy_st_no_ll'] = (base_ma_line + hh_session + src_c) / 3.0 # Upper Boundary Line
    df['pxy_st_no_hh'] = (base_ma_line + ll_session + src_c) / 3.0 # Lower Boundary Line
    df['bar_count_session'] = bar_count_session
    df['src_c'] = src_c

    # Dashboard Compatibility Reference Keys from original structure
    df['ST'] = df['pxy_st_line'] 
    df['c1'] = pd.Series(src_c).shift(1).to_numpy()
    df['st_prev'] = df['ST'].shift(1) 

    # 4. HISTORICAL STATE & MOMENTUM TREND COMPILER LOOPS
    st = df['pxy_st_line'].to_numpy()
    no_ll = df['pxy_st_no_ll'].to_numpy()
    no_hh = df['pxy_st_no_hh'].to_numpy()
    
    st_trend_full = [] 
    
    for i in range(n): 
        if bar_count_session[i] < 2: 
            st_trend_full.append("BULL" if src_c[i] >= st[i] else "BEAR") 
            continue 
            
        c0 = src_c[i]
        c1 = src_c[i-1]
        st0 = st[i]
        st1 = st[i-1]
        
        # Center Line Crossovers
        cross_buy  = (c0 > st0) and (c1 <= st1)
        cross_sell = (c0 < st0) and (c1 >= st1)
        
        # Boundary Line Intersections
        force_buy  = (c0 > no_ll[i]) and (c1 <= no_ll[i-1])
        force_sell = (c0 < no_hh[i]) and (c1 >= no_hh[i-1])
        
        # Priority Structural Trend Matrix Evaluation
        if force_buy:
            st_trend_full.append("FORCESELL")
        elif force_sell:
            st_trend_full.append("FORCEBUY")
        elif cross_buy:
            st_trend_full.append("CROSSBUY")
        elif cross_sell:
            st_trend_full.append("CROSSSELL")
        else:
            # Maintain underlying market baseline tracker state
            st_trend_full.append("BULL" if c0 >= st0 else "BEAR")

    df['st_trend_full'] = st_trend_full
    return df

def get_signal(df: pd.DataFrame) -> tuple:
    """
    Direct endpoint extractor matching lookups with your Pine configuration switch properties.
    """
    if df is None or df.empty:
        return "NONE", "NONE"
        
    try:
        # Run raw historical data frame straight through your calculated Supertrend driver matrix
        calculated_df = calculate_supertrend(df)
        n = len(calculated_df)
        
        # Resolve array lookups matching your exact Pine switches
        if CHECK_CONFIRMED_ONLY:
            idx = n - 2  # 🔒 Completed Candle (Non-Reprinting)
        else:
            idx = n - 1  # ⚡ Live Running Candle (Real-Time Tracker)
            
        entry_sig = str(calculated_df.at[calculated_df.index[idx], 'st_trend_full']).upper().strip()
        exit_sig = entry_sig
        
        if DEBUG_MODE:
            print(f"--- PXY ENGINE CONSOLE SUMMARY ---")
            print(f"Target Row Lookup Index   -> {idx}")
            print(f"Session Bar Intraday Count -> {calculated_df.at[calculated_df.index[idx], 'bar_count_session']}")
            print(f"Active Live Market Signal  -> {entry_sig}\n")
            
        return entry_sig, exit_sig
        
    except Exception as e:
        if DEBUG_MODE:
            print(f"PXY Master Output Routing Module Exception: {e}")
        return "NONE", "NONE"

# --- STANDALONE PRODUCTION LISTENER GATE ---
if __name__ == "__main__":
    from sysdthapxy import get_pxy_data
    
    print("\n[PXY STRND ENGINE] Standalone Live Stream Listener Initiated.")
    print(f"Configuration -> CHECK_CONFIRMED_ONLY: {CHECK_CONFIRMED_ONLY}")
    print("--------------------------------------------------")
    
    try:
        print("Polling latest day-specific data from sysdthapxy...")
        _, _, _, live_df = get_pxy_data(df=None)
        
        if live_df is not None and not live_df.empty:
            print(f"Data Successfully Retrieved. Array length: {len(live_df)} intervals.")
            entry_sig, exit_sig = get_signal(live_df)
            
            print("==================================================")
            print(f"⚡ LIVE STREAM OUTPUT -> Entry: {entry_sig} | Exit: {exit_sig}")
            print("==================================================\n")
        else:
            print("❌ Error: Upstream module returned an empty or invalid DataFrame frame.")
            
    except Exception as e:
        print(f"❌ Critical Connection Exception Hit: {e}")

