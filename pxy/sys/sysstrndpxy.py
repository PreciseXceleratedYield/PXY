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
    Processes a 1-minute Heikin Ashi framework with a 14-period TSMA middle line, 
    14-period ATR bands, and a 15-minute Heikin Ashi macro open anchor line.
    
    TREND DEFINITION: 
    - BULL: 1m HA Close is ABOVE or EQUAL to the 15m HA Open line.
    - BEAR: 1m HA Close is BELOW the 15m HA Open line.
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

    # 1. TIMELINE ISOLATION: FILTER FOR TODAY'S SESSION ONLY
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

    # 2. CONVERT STANDARD CANDLES TO PURE HEIKIN-ASHI 1-MINUTE ARRAYS
    src_o = df['Open'].to_numpy()
    src_h = df['High'].to_numpy()
    src_l = df['Low'].to_numpy()
    src_c = df['Close'].to_numpy()

    ha_open  = np.zeros(n)
    ha_high  = np.zeros(n)
    ha_low   = np.zeros(n)
    ha_close = np.zeros(n)

    # Sequence Loop Initialization using exact 100% element-wise mathematical vectors
    ha_close = (src_o + src_h + src_l + src_c) / 4.0
    ha_open  = (src_o + src_c) / 2.0
    ha_high  = np.maximum(src_h, np.maximum(ha_open, ha_close))
    ha_low   = np.minimum(src_l, np.minimum(ha_open, ha_close))

    # Rolling processing to build a mirror copy of TradingView's internal chart values
    for i in range(1, n):
        ha_close[i] = (src_o[i] + src_h[i] + src_l[i] + src_c[i]) / 4.0
        ha_open[i]  = (ha_open[i-1] + ha_close[i-1]) / 2.0
        ha_high[i]  = max(src_h[i], ha_open[i], ha_close[i])
        ha_low[i]   = min(src_l[i], ha_open[i], ha_close[i])

    # Re-wrap into Series structures for clean technical rolling indexes
    ha_close_ser = pd.Series(ha_close, index=df.index)
    ha_high_ser  = pd.Series(ha_high, index=df.index)
    ha_low_ser   = pd.Series(ha_low, index=df.index)

    # 3. TSMA 14 & ATR 14 BAND CALCULATIONS (PURE NUMPY POINTERS)
    tsma_len = 14
    atr_len = 14
    atr_mult = 1.5

    # TSMA 14 Calculation utilizing sequential linear regressions
    tsma_1m = np.zeros(n)
    x_reg = np.arange(tsma_len)
    sum_x = np.sum(x_reg)
    sum_xx = np.sum(x_reg ** 2)
    denom = (tsma_len * sum_xx) - (sum_x ** 2)

    for i in range(n):
        if i < tsma_len - 1:
            tsma_1m[i] = ha_close_ser.iloc[i]
        else:
            y_sub = ha_close_ser.iloc[i - tsma_len + 1 : i + 1].to_numpy()
            sum_y = np.sum(y_sub)
            sum_xy = np.sum(x_reg * y_sub)
            slope = ((tsma_len * sum_xy) - (sum_x * sum_y)) / denom
            intercept = (sum_y - (slope * sum_x)) / tsma_len
            tsma_1m[i] = (slope * (tsma_len - 1)) + intercept

    # ATR 14 Calculation matching TradingView's RMMA smoothing technique
    tr = np.zeros(n)
    tr = ha_high_ser.iloc - ha_low_ser.iloc
    for i in range(1, n):
        hl = ha_high_ser.iloc[i] - ha_low_ser.iloc[i]
        hc_prev = ha_close_ser.iloc[i-1]
        h_cp = abs(ha_high_ser.iloc[i] - hc_prev)
        l_cp = abs(ha_low_ser.iloc[i] - hc_prev)
        tr[i] = max(hl, h_cp, l_cp)

    atr_1m = np.zeros(n)
    if n >= atr_len:
        atr_1m[atr_len-1] = np.mean(tr[:atr_len])
        for i in range(atr_len, n):
            atr_1m[i] = (atr_1m[i-1] * (atr_len - 1) + tr[i]) / atr_len
    else:
        atr_1m[:] = tr[:]

    upper_band = tsma_1m + (atr_1m * atr_mult)
    lower_band = tsma_1m - (atr_1m * atr_mult)

    # 4. 15-MINUTE HA MACRO OPEN TRACKING ENGINE (lookahead_on processing layout)
    df_15m = df.resample('15min').agg({'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last'}).dropna()
    n_15 = len(df_15m)
    ha_open_15_arr = np.zeros(n_15)
    
    if n_15 > 0:
        o_15 = df_15m['Open'].to_numpy()
        h_15 = df_15m['High'].to_numpy()
        l_15 = df_15m['Low'].to_numpy()
        c_15 = df_15m['Close'].to_numpy()
        
        c_15_ha = (o_15 + h_15 + l_15 + c_15) / 4.0
        ha_open_15_arr = (o_15 + c_15) / 2.0
        for i in range(1, n_15):
            ha_open_15_arr[i] = (ha_open_15_arr[i-1] + c_15_ha[i-1]) / 2.0
            
    df_15m['HA_15m_Open'] = ha_open_15_arr
    df_joined = df.join(df_15m['HA_15m_Open']).ffill()
    ha_15m_open_line = df_joined['HA_15m_Open'].fillna(ha_close_ser.iloc).to_numpy()

    # Save target parameters to system storage indicators
    df['pxy_st_line'] = tsma_1m
    df['bar_count_session'] = np.arange(1, n + 1)
    df['src_c'] = ha_close 

    # 5. MULTI-INTERVAL MATCHING SIGNAL ENGINE (BB/BS, MB/MS, CB/CS)
    st_signal_history = [] 
    st_trend_history = []
    
    for i in range(n):
        # 🎯 TREND DEFINITION OVERRIDE: 1m HA close vs 15m HA open line
        current_trend = "BULL" if ha_close[i] >= ha_15m_open_line[i] else "BEAR"
        st_trend_history.append(current_trend)

        if i < 1:
            st_signal_history.append("NONE")
            continue

        active_signals_list = []

        # Rule 2 & 3: Extreme Band Wick Touches
        if ha_high_ser.iloc[i] >= upper_band[i]:
            active_signals_list.append("BS")
        if ha_low_ser.iloc[i] <= lower_band[i]:
            active_signals_list.append("BB")

        # Rule 4: Middle TSMA Line Crosses
        if ha_close_ser.iloc[i] > tsma_1m[i] and ha_close_ser.iloc[i-1] <= tsma_1m[i-1]:
            active_signals_list.append("MB")
        elif ha_close_ser.iloc[i] < tsma_1m[i] and ha_close_ser.iloc[i-1] >= tsma_1m[i-1]:
            active_signals_list.append("MS")

        # Rule 5: 15m HA Line Crosses
        if ha_close_ser.iloc[i] > ha_15m_open_line[i] and ha_close_ser.iloc[i-1] <= ha_15m_open_line[i-1]:
            active_signals_list.append("CB")
        elif ha_close_ser.iloc[i] < ha_15m_open_line[i] and ha_close_ser.iloc[i-1] >= ha_15m_open_line[i-1]:
            active_signals_list.append("CS")

        # Append unified text block tags
        if active_signals_list:
            st_signal_history.append("/".join(active_signals_list))
        else:
            st_signal_history.append("NONE")

    df['st_signal_full'] = st_signal_history
    df['st_trend_full'] = st_trend_history
    
    # 🎯 DASHBOARD BACKWARD-COMPATIBILITY ARRAYS
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
    
    # 1. Fallback Global Variable Integrity Check (Prevents compilation crash if configuration module is empty)
    try:
        active_ticker = TICKER
        active_tz = TIMEZONE
    except NameError:
        active_ticker = "AAPL"
        active_tz = "America/New_York"
        print(f"ℹ️ Config module references not found. Falling back to default: {active_ticker} | {active_tz}")

    # 2. Run Test Run Validation using Fallback Multi-Day Stream Block
    print(f"📥 Pulling live market records to verify matrix convergence for: {active_ticker}...")
    dummy = pd.DataFrame()
    
    # Calculate signals and process chart JSON payload dump
    signal, trend = get_signal(dummy)
    exported_data = export_supertrend_json()
    
    # 3. Print Active Real-Time Engine Execution Dashboard
    if exported_data and len(exported_data) > 0:
        print("\n==================================================")
        print("📊 STRATEGY LIVE PERFORMANCE METRIC SNAPSHOT")
        print("==================================================")
        print(f"📡 Current Time Context  : {datetime.now(pytz.timezone(str(active_tz))).strftime('%Y-%m-%d %H:%M:%S')} ({active_tz})")
        print(f"🔑 Targeted Asset Symbol : {active_ticker}")
        print(f"📉 Matrix Processing Rows: {len(exported_data)} total candles compiled inside session frame.")
        print(f"🟢 Active Output Trend   : [ {trend} ]")
        print(f"⚡ Active Output Signal  : [ {signal} ]")
        print("==================================================")
        
        # Display the last 5 operational logs from the processed stream matrix array
        print("\n📋 RECENT MATRICES ROW TIMELINE (Last 5 Logs):")
        full_df = calculate_supertrend(dummy)
        triggered_only = full_df[full_df['st_signal_full'] != "NONE"]
        
        if not triggered_only.empty:
            for timestamp, row in triggered_only.tail(5).iterrows():
                print(f" 🕒 {timestamp.strftime('%H:%M')} -> Close: {row['src_c'][-1] if isinstance(row['src_c'], np.ndarray) else row['src_c']:.2f} | Signals Hit: [ {row['st_signal_full']} ]")
        else:
            print(" No strategy breakout events detected inside this data segment.")
        print("==================================================\n")
    else:
        print("\n❌ Error: Critical Data Failure. Market streaming matrix failed to process.")

