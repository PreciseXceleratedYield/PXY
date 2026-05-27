# sysentrpxy.py
from sysstrndpxy import calculate_supertrend  # <-- Import Tier 1 42 TSMA Engine
from sysmktpxy import get_signal  # <-- Import Tier 2 Network Layer (BULL/BEAR Pure Layer)
try:
    from syscnfgpxy import TICKER
except ImportError:
    TICKER = "NSE_INDEX"
import pandas as pd
import datetime
from zoneinfo import ZoneInfo  # Robust built-in timezone library

def get_entry_signal(df=None):
    # Extract Tier 1 Underlying 42 TSMA Trend States
    st_trend = "SIDE"
    if df is not None and not df.empty:
        try:
            df_st = calculate_supertrend(df)
            st_trend = str(df_st['ST_Trend'].iloc[-1]).upper()
        except Exception:
            st_trend = "SIDE"

    # --- INDEPENDENT MARKET EXIT LAYER EXTRACTION ---
    # Fetch background context directly from sysmktpxy module independently
    mkt_entry, mkt_exit = "NONE", "NONE"
    if df is not None and not df.empty:
        try:
            mkt_entry, mkt_exit = get_signal(df)
            mkt_exit = str(mkt_exit).upper().strip()
        except Exception:
            mkt_exit = "NONE"

    # --- SYNC EXIT LAYER INDEPENDENTLY FROM SYSMKTPXY ---
    if mkt_exit in ["BULL", "BEAR", "NONE"]:
        exit_signal = mkt_exit
    else:
        exit_signal = "NONE"

    # Initialize entry signal to clean baseline neutral state
    final_signal = "NONE"

    # --- TIME-BASED PRIORITY ROUTER OVERRIDE (09:15 - 10:15 IST Locked) ---
    is_morning_window = False
    if df is not None and not df.empty:
        try:
            latest_time = df.index[-1]
            # Convert string index to timestamp object if necessary
            if not isinstance(latest_time, pd.Timestamp):
                ts = pd.to_datetime(latest_time)
            else:
                ts = latest_time
            
            # Strict Timezone Conversion to Indian Standard Time (IST)
            if ts.tzinfo is None:
                # If naive, assume it's already IST from your Indian broker data feed
                ts_ist = ts.replace(tzinfo=ZoneInfo("Asia/Kolkata"))
            else:
                # If localized (e.g. UTC from Yahoo Finance), cleanly shift it to IST
                ts_ist = ts.tz_convert("Asia/Kolkata")
                
            current_time = ts_ist.time()
            
            start_window = datetime.time(9, 15)
            end_window = datetime.time(10, 15)
            
            if start_window <= current_time <= end_window:
                is_morning_window = True
        except Exception:
            is_morning_window = False

    # Route based on time priority window
    if is_morning_window:
        if exit_signal == "BULL":
            final_signal = "OTMBUY"
        elif exit_signal == "BEAR":
            final_signal = "OTMSELL"
        else:
            final_signal = "NONE"
            
    # --- NORMAL MODE ROUTER (BEFORE 9:15 OR AFTER 10:15 IST) ---
    else:
        # 1. ATMBUY Channel Configurations (Crossovers & Trajectory Channel Swings)
        if st_trend in ["CROSSBUY", "TRENDBUY"]:
            final_signal = "ATMBUY"
            
        # 2. OTMBUY Channel Configurations (Extreme Force Boundary Breakouts)
        elif st_trend == "FORCEBUY":
            final_signal = "OTMBUY"
            
        # 3. ATMSELL Channel Configurations (Crossovers & Trajectory Channel Swings)
        elif st_trend in ["CROSSSELL", "TRENDSELL"]:
            final_signal = "ATMSELL"
            
        # 4. OTMSELL Channel Configurations (Extreme Force Boundary Breakouts)
        elif st_trend == "FORCESELL":
            final_signal = "OTMSELL"
            
        # 5. Unfiltered Trend States Pass-Through
        elif st_trend in ["BULL", "BEAR"]:
            final_signal = st_trend
            
        # Fallback handling for early initialization rows ("SIDE")
        else:
            final_signal = "NONE"

    # --- SEPARATED ACTION VS. INFORMATIONAL LOGGER ---
    is_live_action = final_signal in ["ATMBUY", "ATMSELL", "OTMBUY", "OTMSELL"]
    window_tag = "[⏱️ IST MORNING]" if is_morning_window else "[⚙️ NORMAL MODE]"
    
    if is_live_action:
        print(f"🔥 {window_tag} ENTRY : {final_signal} | EXIT: {exit_signal} | TREND: {st_trend} 🔥")
    elif final_signal in ["BULL", "BEAR"]:
        print(f"ℹ️ {window_tag} ENTRY : {final_signal} | EXIT: {exit_signal} | TREND: {st_trend}")
    else:
        print(f"💤 {window_tag} ENTRY : {final_signal} | EXIT: {exit_signal} | TREND: {st_trend}")

    return final_signal, exit_signal

if __name__ == "__main__":
    from sysdtafpxy import fetch_yf_data
    print("\n=== [TIER 3] Unified STRND Entry + Independent MKT Exit Pipeline Self-Test ===")
    df = fetch_yf_data()
    if df is not None:
        entry, ex = get_entry_signal(df)
        print("-" * 50)
        print(f"FINAL ENTRY SIGNAL: {entry} | EXIT SIGNAL: {ex}")


