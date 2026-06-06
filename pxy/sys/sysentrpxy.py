# sysentrpxy.py
"""
===============================================================================
PXY OPTION ROUTING ENGINE: SUPERTREND & SMA DUAL-PIPE COUPLING
===============================================================================
Operational Rules:
- EXIT and ENTRY signals originate strictly from sysmktpxy (exit_sig, entry_sig).
- ENTRY Layer A (👑 PRIORITY 1): Pure Dual-Pipe Crossover Line Switches.
  Fires instantly when 'strnd_trend' OR 'sma_trend' hits 'BUY' or 'SELL'.
- ENTRY Layer B (⚡ PRIORITY 2): Pure structural breakouts from sysbbospxy (bos_signal).
- ENTRY Layer C (📈 PRIORITY 3): Trend-following option contract assignment.
  Triggers BUY if (entry_sig == BUY or exit_sig == BUY) AND (sma_trend == BULL or strnd_trend == BULL).
  Triggers SELL if (entry_sig == SELL or exit_sig == SELL) AND (sma_trend == BEAR or strnd_trend == BEAR).
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
        if exit_sig == "BUY":
            final_signal = "ATMBUY"
        elif exit_sig == "SELL":
            final_signal = "ATMSELL"
        else:
            final_signal = "NONE"
    else:
        if DEBUG_MODE:
            print("🏙️ CURRENT TIMING STATE: Standard Continuous window logic active.")
            print(f"🛡️ STEP 1: Testing Priority 1 Dual Crossovers (ST: '{strnd_trend}', SMA: '{sma_trend}')...")
        
        # 👑 PRIORITY 1: Native Dual-Pipeline Crossovers (Either Pipe A OR Pipe B Crossovers Trigger Instantly)
        if strnd_trend == "BUY" or sma_trend == "BUY":
            if DEBUG_MODE:
                print("  🏆 PRIORITY 1 UNLOCKED: Absolute Bullish Crossover confirmed.")
            final_signal = "ATMBUY"
        elif strnd_trend == "SELL" or sma_trend == "SELL":
            if DEBUG_MODE:
                print("  🏆 PRIORITY 1 UNLOCKED: Absolute Bearish Breakdown confirmed.")
            final_signal = "ATMSELL"
            
        # ⚡ PRIORITY 2: High-Volume 42-Min Structural Breakouts (sysbbospxy)
        else:
            if DEBUG_MODE:
                print(f"  ↳ Priority 1 is inactive. Falling to Step 2: Testing Priority 2 Breakouts (bos_signal == '{bos_signal}')...")
            if bos_signal == "BUY":
                if DEBUG_MODE:
                    print("  ⚡ PRIORITY 2 UNLOCKED: Bullish BOS Structural Breakout approved.")
                final_signal = "ATMBUY"
            elif bos_signal == "SELL":
                final_signal = "ATMSELL"
                if DEBUG_MODE:
                    print("  ⚡ PRIORITY 2 UNLOCKED: Bearish BOS Structural Breakdown approved.")

            # 📈 PRIORITY 3: Trend-Following Pullback and Running Regimes Gates
            else:
                if DEBUG_MODE:
                    print(f"    ↳ Priority 2 is 'NONE'. Falling to Step 3: Testing Priority 3 (entry='{entry_sig}', exit='{exit_sig}', ST_Trend='{strnd_trend}', SMA_Trend='{sma_trend}')...")
                
                # 🎯 EITHER/OR LOOKUP ARRAYS
                is_signal_buy = (entry_sig == "BUY" or exit_sig == "BUY")
                is_trend_bull = (sma_trend == "BULL" or strnd_trend == "BULL")

                is_signal_sell = (entry_sig == "SELL" or exit_sig == "SELL")
                is_trend_bear = (sma_trend == "BEAR" or strnd_trend == "BEAR")

                # 🚀 Pullback trigger tracking using your exact dual environmental trend qualification
                if is_signal_buy and is_trend_bull:
                    if DEBUG_MODE:
                        print("  🚀 PRIORITY 3 UNLOCKED: Trend Pullback Dynamic Entry approved.")
                    final_signal = "ATMBUY"
                elif is_signal_sell and is_trend_bear:
                    if DEBUG_MODE:
                        print("  🚀 PRIORITY 3 UNLOCKED: Trend Pullback Dynamic Entry approved.")
                    final_signal = "ATMSELL"
                else:
                    if DEBUG_MODE:
                        print("    ❌ All waterfall priority logic gates failed to match execution parameters.")
                    final_signal = "NONE"

    # 5. OPTIMIZED TELEMETRY ALERT ENGINE
    if DEBUG_MODE:
        print(f"🏁 FINAL ROUTING ENGINE DECISION VALUE: '{final_signal}'")
    
    if final_signal in ["ATMBUY", "ATMSELL", "OTMBUY", "OTMSELL"]:
        print(f"⏰ [IST: {current_time_ist.strftime('%H:%M:%S')}] 🔥 ACTION-{final_signal} 🔥 ".center(40))

    if DEBUG_MODE:
        print("═" * 43 + "\n")
        
    return final_signal, exit_sig

if __name__ == "__main__":
    print("\n[PXY ROUTER STATUS] Upstream Filtered Option Route Matrix Active.")
    print("-" * 50)
    final_route, raw_exit = get_entry_signal(df=None)
    print("-" * 50)
