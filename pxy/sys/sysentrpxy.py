# ===============================================================================
# PART 1: MODULE INGESTION, CONFIGURATION, AND DATA PIPELINE MATRIX
# ===============================================================================
# sysentrpxy.py
"""
===============================================================================
PXY OPTION ROUTING ENGINE: SUPERTREND & SMA DUAL-PIPE COUPLING
===============================================================================
Operational Rules:
- EXIT and ENTRY signals originate strictly from sysmktpxy (exit_sig, entry_sig).
- ENTRY Layer A (👑 PRIORITY 1): Pure Dual-Pipe Crossover Line Switches.
  Fires instantly when 'strnd_trend' OR 'sma_trend' hits 'BUY' or 'SELL'.
  Assigns ATM contracts on line crossovers.
- ENTRY Layer B (⚡ PRIORITY 2): Pure structural breakouts from sysbbospxy (bos_signal).
- ENTRY Layer C (📈 PRIORITY 3): Trend-following option contract assignment.
  Triggers ATMSELL if signal is SELL AND both trends are BULL (Aligned).
  Triggers ATMBUY if signal is BUY AND both trends are BEAR (Aligned).
  Triggers OTMBUY if signal is BUY AND any trend is BULL (Partial/Unaligned).
  Triggers OTMSELL if signal is SELL AND any trend is BEAR (Partial/Unaligned).
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
# True = Output full, deep multi-layered telemetry logs
# False = Silence dashboard chatter completely, only log final actions/errors
DEBUG_MODE = False

# 🛠️ LOCAL CONFIGURATION FALLBACK
# True = Target the closed candle index (-2) | False = Target live running index (-1)
CHECK_CONFIRMED_ONLY = False

# 🛠️ INDEPENDENT STRATEGY SWITCHES
ENABLE_EARLY_MORNING_WINDOW = True  # True = Process 09:15-09:30 entries | False = Skip layer completely
ENABLE_BOS_BREAKOUT_ENGINE  = True  # True = Process structural breakouts     | False = Skip layer completely

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
    sma_trend = "NEUTRAL"

    if strnd_df is not None and not strnd_df.empty:
        idx = -2 if CHECK_CONFIRMED_ONLY else -1
        if DEBUG_MODE:
            print(f"  -> Target lookup row index: {idx} (CHECK_CONFIRMED_ONLY: {CHECK_CONFIRMED_ONLY})")
        try:
            strnd_trend = str(strnd_df.iloc[idx]['st_trend_full']).upper().strip()   # Pipe A: 3:3 Supertrend
            sma_trend   = str(strnd_df.iloc[idx]['sma_trend_full']).upper().strip()  # Pipe B: 42 Rolling SMA
            if DEBUG_MODE:
                print(f"  -> [sysstrndpxy] Pipe A (Supertrend): '{strnd_trend}' | Pipe B (42 SMA): '{sma_trend}'")
        except Exception as e:
            print(f"  ❌ ERROR parsing sysstrndpxy array columns: {e}")
            print(traceback.format_exc())
    else:
        if DEBUG_MODE:
            print("  ⚠️ Warning: calculate_supertrend returned an empty or Null DataFrame.")
# ===============================================================================
# PART 2: TIME ENGINE AND REORDERED WATERFALL ROUTING LOGIC
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
            if DEBUG_MODE:
                print("  ⚠️ Early morning entry layer disabled. Skipping signal assignment.")
            final_signal = "NONE"
            
    else:
        if DEBUG_MODE:
            print("🏙️ CURRENT TIMING STATE: Standard Continuous window logic active.")
            print(f"🛡️ STEP 1: Testing Priority 1 Dual Crossovers (ST: '{strnd_trend}', SMA: '{sma_trend}')...")
        
        # 👑 PRIORITY 1: Native Dual-Pipeline Crossovers (Fires instantly on line crossings -> now assigned to ATM)
        if strnd_trend == "BUY" or sma_trend == "BUY":
            if DEBUG_MODE:
                print("  🏆 PRIORITY 1 UNLOCKED: Absolute Bullish Crossover confirmed.")
            final_signal = "ATMBUY"
        elif strnd_trend == "SELL" or sma_trend == "SELL":
            if DEBUG_MODE:
                print("  🏆 PRIORITY 1 UNLOCKED: Absolute Bearish Breakdown confirmed.")
            final_signal = "ATMSELL"
            
        # ⚡ PRIORITY 2: High-Volume 42-Min Structural Breakouts (sysbbospxy)
        elif ENABLE_BOS_BREAKOUT_ENGINE:
            if DEBUG_MODE:
                print(f"  ↳ Priority 1 is inactive. Falling to Step 2: Testing Priority 2 Breakouts (bos_signal == '{bos_signal}')...")
            if bos_signal == "BUY":
                if DEBUG_MODE:
                    print("  ⚡ PRIORITY 2 UNLOCKED: Bullish BOS Structural Breakout approved.")
                final_signal = "OTMBUY"
            elif bos_signal == "SELL":
                if DEBUG_MODE:
                    print("  ⚡ PRIORITY 2 UNLOCKED: Bearish BOS Structural Breakout approved.")
                final_signal = "OTMSELL"
            else:
                # Fallback to Priority 3 if BOS layer is ON but returns no signal
                if DEBUG_MODE:
                    print("  ↳ Priority 2 active but no breakout found. Falling to Step 3...")
                
                # --- STRICT DUAL-TREND ALIGNMENT RULES (AND -> ATM | OR -> OTM) ---
                if entry_sig == "SELL" and strnd_trend == "BULL" and sma_trend == "BULL":
                    final_signal = "ATMSELL"
                elif entry_sig == "BUY" and strnd_trend == "BEAR" and sma_trend == "BEAR":
                    final_signal = "ATMBUY"
                elif entry_sig == "BUY" and (strnd_trend == "BULL" or sma_trend == "BULL"):
                    final_signal = "OTMBUY"
                elif entry_sig == "SELL" and (strnd_trend == "BEAR" or sma_trend == "BEAR"):
                    final_signal = "OTMSELL"
                else:
                    final_signal = "NONE"
        
        # 📈 PRIORITY 3: Fallback straight here if Priority 1 is inactive AND the BOS switch is turned off
        else:
            if DEBUG_MODE:
                print("  ⏩ Priority 2 Engine is OFF. Skipping straight to Priority 3 Trend Assignment...")
            
            # --- STRICT DUAL-TREND ALIGNMENT RULES (AND -> ATM | OR -> OTM) ---
            if entry_sig == "SELL" and strnd_trend == "BULL" and sma_trend == "BULL":
                final_signal = "ATMSELL"
            elif entry_sig == "BUY" and strnd_trend == "BEAR" and sma_trend == "BEAR":
                final_signal = "ATMBUY"
            elif entry_sig == "BUY" and (strnd_trend == "BULL" or sma_trend == "BULL"):
                final_signal = "OTMBUY"
            elif entry_sig == "SELL" and (strnd_trend == "BEAR" or sma_trend == "BEAR"):
                final_signal = "OTMSELL"
            else:
                final_signal = "NONE"

    return final_signal, exit_sig

