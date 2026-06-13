# ===============================================================================
# FINAL MASTER PRODUCTION MATRIX: STREAMLINED SIMPLIFIED 4-TIER WATERFALL
# ===============================================================================
# sysentrpxy.py
"""
===============================================================================
PXY OPTION ROUTING ENGINE: FINAL MASTER PRODUCTION MATRIX
===============================================================================
Operational Rules:
- EXIT and ENTRY signals originate strictly from sysmktpxy (exit_sig, entry_sig).
- REQUIREMENT: entry_sig is explicitly set equal to exit_sig.
- PRESERVATION LOCK: exit_sig from sysmktpxy is preserved unmutated to the very end.

Waterfall Priorities:
- 👑 PRIORITY 1: All BOS Breakouts (MBUY / NBUY / MSELL / NSELL) -> Assigned strictly to ATM.
- 🏆 PRIORITY 2: Jumping SMA Crossovers (TBUY / TSELL Only) -> Assigned strictly to ATM.
- 📊 DIRECT ALIGNMENT ROUTING MATRIX:
    - If entry is BUY and trend line is BULL/TBUY  -> ATMBUY (Priority 3)
    - If entry is BUY and trend line is BEAR/TSELL -> OTMBUY (Priority 4)
    - If entry is SELL and trend line is BEAR/TSELL -> ATMSELL (Priority 3)
    - If entry is SELL and trend line is BULL/TBUY  -> OTMSELL (Priority 4)
===============================================================================
"""

import pandas as pd
from datetime import datetime
from zoneinfo import ZoneInfo
import traceback  

# Ingestion gateways from your exact strategy matrix modules
from sysmktpxy import get_signal
from sysstrndpxy import calculate_supertrend
from sysbbospxy import get_bos_bar  
from syscnfgpxy import TICKER

# 🛠️ GLOBAL DEBUGGING SWITCH
DEBUG_MODE = False

# 🛠️ LOCAL CONFIGURATION FALLBACK
CHECK_CONFIRMED_ONLY = False

def get_entry_signal(df=None):
    """
    Master Option Router Orchestrator.
    Ingests simplified BUY/SELL framework signals and routes via a structured, 
    multi-tier waterfall to output targeted contract tiers.
    """
    if DEBUG_MODE:
        print("\n" + "🔍 DEBUG START: INITIALIZING ROUTER SCAN 🔍".center(60, "═"))
    
    # Initialize baseline string states to guarantee scope safety across error gates
    raw_entry = "NONE"
    
    # 1. DATA SYNCHRONIZATION AND MULTI-INDEX HEADER FLATTENING
    if df is None or df.empty:
        if DEBUG_MODE:
            print("💡 Dataframe empty or None. Fetching fresh continuous stream buffer...")
        import yfinance as yf
        ticker_obj = yf.Ticker(TICKER)
        df = ticker_obj.history(period="5d", interval="1m")
        
    if df.empty:
        print("❌ CRITICAL: Data stream returned an empty dataframe from yfinance framework.")
        return "NONE", "NONE"
        
    master_df = df.copy()
    
    # Clean up multi-index column structures safely to avoid quiet KeyError failures
    if isinstance(master_df.columns, pd.MultiIndex):
        if DEBUG_MODE:
            print("🛠️ MultiIndex column detected. Flattening columns to avoid KeyError loops...")
        master_df.columns = master_df.columns.get_level_values(0)

    # 2. SEGREGATED STRATEGY MODULE INGESTION PIPELINES
    if DEBUG_MODE:
        print("📡 Pulling execution states from strategy pipes...")
        
    try:
        # Unpack both the asymmetric confirmed Entry and the live running Exit variables
        # Note: We capture the simplified raw_entry (BUY/SELL) from sysmktpxy here
        raw_entry, exit_sig = get_signal(master_df)
        raw_entry = str(exit_sig).upper().strip()
        exit_sig = str(exit_sig).upper().strip()
        
        # 🚨 Explicit production requirement: entry_sig maps to exit_sig for transitional triggers
        entry_sig = exit_sig
        
        if DEBUG_MODE:
            print(f"  -> [sysmktpxy] Raw Entry Signal: '{entry_sig}' | Exit Signal: '{exit_sig}'")
    except Exception as e:
        print(f"  ❌ ERROR inside sysmktpxy pipeline: {e}")
        entry_sig, exit_sig = "NONE", "NONE"
        raw_entry = "NONE"

    try:
        # Extract breakout signals from your 42-min structural breakout engine
        _, bos_signal = get_bos_bar(master_df)
        bos_signal = str(bos_signal).upper().strip()
        if DEBUG_MODE:
            print(f"  -> [sysbbospxy] Raw BOS Breakout Signal: '{bos_signal}'")
    except Exception as e:
        print(f"  ❌ ERROR inside sysbbospxy pipeline: {e}")
        bos_signal = "NONE"

    if DEBUG_MODE:
        print("📊 Evaluating sysstrndpxy modular single-pipeline matrix...")
    strnd_df = calculate_supertrend(master_df)
    
    strnd_trend = "NEUTRAL"

    if strnd_df is not None and not strnd_df.empty:
        idx = -2 if CHECK_CONFIRMED_ONLY else -1
        if DEBUG_MODE:
            print(f"  -> Target lookup row index: {idx} (CHECK_CONFIRMED_ONLY: {CHECK_CONFIRMED_ONLY})")
        try:
            # SOLELY DEPENDING ON THE UNIFIED JUMPING SMA TRACKING LINE
            strnd_trend = str(strnd_df.iloc[idx]['sma_trend_full']).upper().strip()   
            if DEBUG_MODE:
                print(f"  -> [sysstrndpxy] Jumping Line Trend (sma_trend_full): '{strnd_trend}'")
        except Exception as e:
            print(f"  ❌ ERROR parsing sysstrndpxy array columns: {e}")

    # 3. Timezone Synchronization Engine (IST Lock)
    tz_ist = ZoneInfo("Asia/Kolkata")
    current_time_ist = datetime.now(tz_ist).time()

    if strnd_df is not None and not strnd_df.empty:
        try:
            last_timestamp = strnd_df.index[-1]
            if not isinstance(last_timestamp, pd.Timestamp):
                last_timestamp = pd.to_datetime(last_timestamp)
            
            # Force the incoming historical index timestamp into localized IST parameters
            if last_timestamp.tzinfo is None:
                current_time_ist = last_timestamp.tz_localize("UTC").tz_convert(tz_ist).time()
            else:
                current_time_ist = last_timestamp.tz_convert(tz_ist).time()
        except Exception:
            pass

    if DEBUG_MODE:
        print(f"⏰ Synchronized IST Execution Time: {current_time_ist.strftime('%H:%M:%S')}")

    # Determine underlying jumping line structural states cleanly
    is_line_bull = strnd_trend in ["BUY", "TBUY", "BULL"]
    is_line_bear = strnd_trend in ["SELL", "TSELL", "BEAR"]

    # 4. MULTI-PRIORITY OPTIONS ROUTING ENGINE WATERFALL
    final_signal = "NONE"

    # 👑 PRIORITY 1: ALL BOS STRUCTURAL BREAKOUTS (No Time Lock -> ATM Target)
    if bos_signal in ["MBUY", "NBUY", "MSELL", "NSELL"]:
        if DEBUG_MODE:
            print("  👑 PRIORITY 1 UNLOCKED: Structural Breakout verified. Assigning ATM.")
        if bos_signal in ["MBUY", "NBUY"]:
            final_signal = "ATMBUY"
        elif bos_signal in ["MSELL", "NSELL"]:
            final_signal = "ATMSELL"
            
    # 🏆 PRIORITY 2: NATIVE TREND ENGINE CROSSOVERS (TBUY / TSELL Only -> ATM Target Track)
    elif strnd_trend in ["TBUY", "TSELL"]:
        if DEBUG_MODE:
            print("  🏆 PRIORITY 2 UNLOCKED: Absolute Trend Line Crossover confirmed. Assigning ATM.")
        if strnd_trend == "TBUY":
            final_signal = "ATMBUY"
        elif strnd_trend == "TSELL":
            final_signal = "ATMSELL"
            
    # 📊 DIRECT ALIGNMENT ROUTING GATEWAY (Priority 3 & Priority 4)
    # Extracts entry flips using your standard BUY/SELL framework configuration strings
    else:
        if DEBUG_MODE:
            print("  📊 UNLOCKED DIRECT ALIGNMENT ROUTING: Applying simplified trend alignment check.")
        
        if raw_entry == "BUY":
            # Aligned: ATMBUY (P3) | Counter-Trend: OTMBUY (P4)
            final_signal = "ATMBUY" if is_line_bull else "OTMBUY"
            
        elif raw_entry == "SELL":
            # Aligned: ATMSELL (P3) | Counter-Trend: OTMSELL (P4)
            final_signal = "ATMSELL" if is_line_bear else "OTMSELL"
            
        else:
            final_signal = "NONE"

    # 🔒 Pure unaltered pass of exit_sig directly from sysmktpxy out to your automated broker execution layer
    return final_signal, exit_sig

