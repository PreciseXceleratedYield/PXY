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
- 👑 PRIORITY 1 (Counter-Trend): Assigns AVG contracts for position averaging.
- 🏆 PRIORITY 2 (Line Crossovers): Assigns high-sensitivity ATM contracts.
- ⚡ PRIORITY 3 (Structural Breakouts): Assigns structural breakout ATM contracts.
- 📈 PRIORITY 4 (Trend Following Fallback): Assigns budget-friendly OTM contracts.
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

# 🛠️ INDEPENDENT STRATEGY SWITCHES
# CHANGE THESE TO True OR False INDEPENDENTLY ANYTIME
ENABLE_EARLY_MORNING_WINDOW = True  # True = Trade morning window (OTM) | False = Completely skip morning window logic
ENABLE_BOS_BREAKOUT_ENGINE  = True  # True = Trade 42-min Breakouts (ATM) | False = Completely skip breakout engine logic

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
    strnd_trend = "NEUTRAL"

    if strnd_df is not None and not strnd_df.empty:
        idx = -2 if CHECK_CONFIRMED_ONLY else -1
        if DEBUG_MODE:
            print(f"  -> Target lookup row index: {idx} (CHECK_CONFIRMED_ONLY: {CHECK_CONFIRMED_ONLY})")
        try:
            strnd_trend = str(strnd_df.iloc[idx]['st_trend_full']).upper().strip()   # Pipe A: 3:3 Supertrend
            strnd_trend   = str(strnd_df.iloc[idx]['strnd_trend_full']).upper().strip()  # Pipe B: 42 Rolling SMA
            if DEBUG_MODE:
                print(f"  -> [sysstrndpxy] Pipe A (Supertrend): '{strnd_trend}' | Pipe B (42 SMA): '{strnd_trend}'")
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
    is_struct_bull = strnd_trend in ["BUY", "BULL"] and strnd_trend in ["BUY", "BULL"]
    is_struct_bear = strnd_trend in ["SELL", "BEAR"] and strnd_trend in ["SELL", "BEAR"]

    # 4. IST TIME-BASED OPTIONS ROUTING ENGINE
    if market_open <= current_time_ist < time_boundary:
        if DEBUG_MODE:
            print("🌅 CURRENT TIMING STATE: Early Morning opening window logic active.")
        
        if ENABLE_EARLY_MORNING_WINDOW:
            if exit_sig == "BUY":
                final_signal = "OTMBUY"  
            elif exit_sig == "SELL":
                final_signal = "OTMSELL" 
            else:
                final_signal = "NONE"
        else:
            # 🚨 If switch is False, skip morning logic entirely and process live conditions instead
            if DEBUG_MODE:
                print("⏩ Morning Layer is OFF. Falling straight into continuous live engine rules.")
            pass # Fall out of this block to execute standard live routing below instead
            
    # Continuous live processing (executes outside morning hours, or during morning hours if layer is disabled)
    if final_signal == "NONE":
        if DEBUG_MODE:
            print("🏙️ CURRENT TIMING STATE: Standard Continuous window logic active.")
        
        # 👑 PRIORITY 1: STRICT COUNTER-TREND POSITION AVERAGING ENGINE (AVG)
        if entry_sig == "SELL" and is_struct_bull:
            if DEBUG_MODE:
                print("  🚨 AVERAGING LAYER UNLOCKED: Short entry inside structural Bull trend. Assigning AVGSELL.")
            final_signal = "AVGSELL"
            
        elif entry_sig == "BUY" and is_struct_bear:
            if DEBUG_MODE:
                print("  🚨 AVERAGING LAYER UNLOCKED: Long entry inside structural Bear trend. Assigning AVGBUY.")
            final_signal = "AVGBUY"
        
        # 🏆 PRIORITY 2: NATIVE DUAL-PIPELINE CROSSOVERS (ATM Fast Execution)
        elif strnd_trend in ["BUY", "SELL"] or strnd_trend in ["BUY", "SELL"]:
            if DEBUG_MODE:
                print("  🏆 PRIORITY 2 UNLOCKED: Absolute Trend Line Crossover confirmed. Assigning ATM.")
            if strnd_trend == "BUY" or strnd_trend == "BUY":
                final_signal = "ATMBUY"
            elif strnd_trend == "SELL" or strnd_trend == "SELL":
                final_signal = "ATMSELL"
            
        # ⚡ PRIORITY 3: HIGH-VOLUME 42-MIN STRUCTURAL BREAKOUTS (ATM Breakout Execution)
        elif ENABLE_BOS_BREAKOUT_ENGINE:
            if bos_signal == "BUY":
                final_signal = "ATMBUY"
            elif bos_signal == "SELL":
                final_signal = "ATMSELL"
            else:
                # --- PRIORITY 4 FALLBACK INSIDE ENGINE: STANDARD TREND SEGMENTATION (OTM) ---
                if entry_sig == "BUY" and (strnd_trend in ["BUY", "BULL"] or strnd_trend in ["BUY", "BULL"]):
                    final_signal = "OTMBUY"
                elif entry_sig == "SELL" and (strnd_trend in ["SELL", "BEAR"] or strnd_trend in ["SELL", "BEAR"]):
                    final_signal = "OTMSELL"
                else:
                    final_signal = "NONE"
        
        # 📈 PRIORITY 4: Standard Trend-Following Fallback (OTM)
        else:
            if entry_sig == "BUY" and (strnd_trend in ["BUY", "BULL"] or strnd_trend in ["BUY", "BULL"]):
                final_signal = "OTMBUY"
            elif entry_sig == "SELL" and (strnd_trend in ["SELL", "BEAR"] or strnd_trend in ["SELL", "BEAR"]):
                final_signal = "OTMSELL"
            else:
                final_signal = "NONE"

    return final_signal, exit_sig
