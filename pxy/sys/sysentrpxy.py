# ===============================================================================
# PART 1: MODULE INGESTION, CONFIGURATION, AND DATA PIPELINE MATRIX
# ===============================================================================
# sysentrpxy.py
"""
===============================================================================
PXY OPTION ROUTING ENGINE: FINAL MASTER PRODUCTION MATRIX
===============================================================================
Operational Rules:
- EXIT and ENTRY signals originate strictly from sysmktpxy (exit_sig, entry_sig).
- REQUIREMENT: entry_sig is explicitly set equal to exit_sig.
- 🌅 MORNING WINDOW (09:15-09:30): Assigns strictly OTM contracts.
- 👑 PRIORITY 2 (BOS Breakout Engine): Assigns high-sensitivity OTM contracts.
- 🏆 PRIORITY 3 (Supertrend Cross): Assigns structural layout OTM contracts.
- ⚡ PRIORITY 4 (Opposite Flip / Counter-Trend): Assigns AVG contracts.
- 📈 PRIORITY 5 (Trend Following Fallback): Assigns budget-friendly ATM contracts.
===============================================================================
"""

import pandas as pd
from datetime import datetime
from zoneinfo import ZoneInfo
import traceback  # 🛠️ For tracing silent execution loop failures
from syscnfgpxy import TICKER

# Ingestion gateways from your exact strategy matrix modules
from sysmktpxy import get_signal
from sysstrndpxy import calculate_supertrend
from sysbbospxy import get_bos_bar  # Ingesting your 42-min structural breakout engine

# 🛠️ GLOBAL DEBUGGING SWITCH
DEBUG_MODE = False

# 🛠️ LOCAL CONFIGURATION FALLBACK
CHECK_CONFIRMED_ONLY = False

def get_entry_signal(df=None):
    """
    Master Router with Deep Telemetry Monitoring.
    """
    if DEBUG_MODE:
        print("\n" + "🔍 DEBUG START: INITIALIZING ROUTER SCAN 🔍".center(60, "═"))
    
    # 1. DATA SYNCHRONIZATION AND MULTI-INDEX HEADER FLATTENING
    if df is None or df.empty:
        if DEBUG_MODE:
            print("💡 Dataframe empty or None. Fetching fresh 5-day continuous stream buffer from yfinance...")
        import yfinance as yf
        ticker_obj = yf.Ticker(TICKER)
        df = ticker_obj.history(period="5d", interval="1m")
        if DEBUG_MODE:
            print(f"📦 Successfully downloaded data matrix. Shape: {df.shape}")
        
    if df.empty:
        print("❌ CRITICAL: Data stream returned an empty dataframe from yfinance framework.")
        return "NONE", "NONE"
        
    master_df = df.copy()
    
    # Clean up multi-index column structures safely to avoid quiet KeyError failures
    if isinstance(master_df.columns, pd.MultiIndex):
        if DEBUG_MODE:
            print("🛠️ MultiIndex column detected. Flattening columns to avoid KeyError loops...")
        master_df.columns = master_df.columns.get_level_values(0)

    # 2. SEGREGATED INGESTION FLOW VIA INDEPENDENT PIPES
    if DEBUG_MODE:
        print("📡 Pulling execution states from strategy pipes...")
        
    try:
        # Unpack both the asymmetric confirmed Entry and the live running Exit variables
        entry_sig, exit_sig = get_signal(master_df)
        entry_sig = str(entry_sig).upper().strip()
        exit_sig = str(exit_sig).upper().strip()
        
        # 🚨 Explicitly setting entry_sig equal to exit_sig as requested
        entry_sig = exit_sig
        
        if DEBUG_MODE:
            print(f"  -> [sysmktpxy] Raw Entry Signal: '{entry_sig}' | Exit Signal: '{exit_sig}'")
    except Exception as e:
        print(f"  ❌ ERROR inside sysmktpxy pipeline: {e}")
        entry_sig, exit_sig = "NONE", "NONE"

    try:
        _, bos_signal = get_bos_bar(master_df)
        bos_signal = str(bos_signal).upper().strip()
        if DEBUG_MODE:
            print(f"  -> [sysbbospxy] Raw BOS Breakout Signal: '{bos_signal}'")
    except Exception as e:
        print(f"  ❌ ERROR inside sysbbospxy pipeline: {e}")
        bos_signal = "NONE"

    if DEBUG_MODE:
        print("📊 Evaluating sysstrndpxy modular dual-pipeline matrix...")
    strnd_df = calculate_supertrend(master_df)
    
    strnd_trend = "NEUTRAL"

    if strnd_df is not None and not strnd_df.empty:
        idx = -2 if CHECK_CONFIRMED_ONLY else -1
        if DEBUG_MODE:
            print(f"  -> Target lookup row index: {idx} (CHECK_CONFIRMED_ONLY: {CHECK_CONFIRMED_ONLY})")
        try:
            # SOLELY DEPENDING ON SUPERTREND (PIPE A)
            strnd_trend = str(strnd_df.iloc[idx]['st_trend_full']).upper().strip()   
            if DEBUG_MODE:
                print(f"  -> [sysstrndpxy] Supertrend (st_trend_full): '{strnd_trend}'")
        except Exception as e:
            print(f"  ❌ ERROR parsing sysstrndpxy array columns: {e}")
            print(traceback.format_exc())
    else:
        if DEBUG_MODE:
            print("  ⚠️ Warning: calculate_supertrend returned an empty or Null DataFrame.")
# ===============================================================================
# PART 2: TIME ENGINE AND CUSTOM STRIKE ALLOCATION WATERFALL LOGIC
# ===============================================================================
    # 3. Establish Base Current Time in Indian Standard Time (IST)
    tz_ist = ZoneInfo("Asia/Kolkata")
    current_time_ist = datetime.now(tz_ist).time()

    if strnd_df is not None and not strnd_df.empty:
        try:
            last_timestamp = strnd_df.index[-1]
            if not isinstance(last_timestamp, pd.Timestamp):
                last_timestamp = pd.to_datetime(last_timestamp)
            if last_timestamp.tzinfo is not None:
                current_time_ist = last_timestamp.astimezone(tz_ist).time()
            else:
                current_time_ist = last_timestamp.time()
        except Exception:
            pass

    market_open = datetime.strptime("09:15", "%H:%M").time()
    time_boundary = datetime.strptime("09:30", "%H:%M").time()

    if DEBUG_MODE:
        print(f"⏰ Synchronized IST Execution Time: {current_time_ist.strftime('%H:%M:%S')}")
        print(f"🔓 Market Window Threshold Locks: Open={market_open} | Boundary={time_boundary}")

    final_signal = "NONE"

    # Normalize mixed trend statuses across modules safely ("BUY" and "BULL" are treated identically)
    is_struct_bull = strnd_trend in ["BUY", "BULL"]
    is_struct_bear = strnd_trend in ["SELL", "BEAR"]

    # 4. IST TIME-BASED OPTIONS ROUTING ENGINE
    if market_open <= current_time_ist < time_boundary:
        if DEBUG_MODE:
            print("🌅 CURRENT TIMING STATE: Early Morning opening window logic active.")
        
        if exit_sig == "BUY":
            final_signal = "OTMBUY"  
        elif exit_sig == "SELL":
            final_signal = "OTMSELL" 
        else:
            final_signal = "NONE"
            
    # Continuous live processing (executes outside morning hours, or during morning hours if layer yields NONE)
    if final_signal == "NONE":
        if DEBUG_MODE:
            print("🏙️ CURRENT TIMING STATE: Standard Continuous window logic active.")
        
        # 👑 PRIORITY 2: HIGH-VOLUME 42-MIN STRUCTURAL BREAKOUTS (OTM Breakout Execution)
        if bos_signal in ["BUY", "SELL"]:
            if DEBUG_MODE:
                print("  👑 PRIORITY 2 UNLOCKED: High-Volume 42-Min Structural Breakout detected. Assigning OTM.")
            if bos_signal == "BUY":
                final_signal = "OTMBUY"
            elif bos_signal == "SELL":
                final_signal = "OTMSELL"
        
        # 🏆 PRIORITY 3: NATIVE DUAL-PIPELINE CROSSOVERS (OTM Fast Execution)
        elif strnd_trend in ["BUY", "SELL"]:
            if DEBUG_MODE:
                print("  🏆 PRIORITY 3 UNLOCKED: Absolute Trend Line Crossover confirmed. Assigning OTM.")
            if strnd_trend == "BUY":
                final_signal = "OTMBUY"
            elif strnd_trend == "SELL":
                final_signal = "OTMSELL"
            
        # ⚡ PRIORITY 4: OPPOSITE FLIP / STRICT COUNTER-TREND POSITION AVERAGING ENGINE (AVG)
        elif (entry_sig == "SELL" and is_struct_bull) or (entry_sig == "BUY" and is_struct_bear):
            if DEBUG_MODE:
                print("  🚨 PRIORITY 4 UNLOCKED: Opposite Flip. Activating Counter-Trend Averaging. Assigning AVG.")
            if entry_sig == "SELL" and is_struct_bull:
                final_signal = "AVGSELL"
            elif entry_sig == "BUY" and is_struct_bear:
                final_signal = "AVGBUY"

        # 📈 PRIORITY 5: Standard Trend-Following Fallback (ATM)
        else:
            if DEBUG_MODE:
                print("  📈 PRIORITY 5 UNLOCKED: Standard Trend-Following Fallback applying.")
            if entry_sig == "BUY" and is_struct_bull:
                final_signal = "ATMBUY"
            elif entry_sig == "SELL" and is_struct_bear:
                final_signal = "ATMSELL"
            else:
                final_signal = "NONE"

    return final_signal, exit_sig
