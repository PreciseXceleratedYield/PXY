"""
===============================================================================
PXY OPTION ROUTING ENGINE: HIGH-VELOCITY UPSTREAM-FILTERED ENGINE (DEBUG DEPLOY)
===============================================================================
Operational Rules:
- EXIT signals originate strictly from sysmktpxy (exit_sig).
- ENTRY Layer A (👑 PRIORITY 1): Pure structural breakout from sysbbospxy (bos_signal).
- ENTRY Layer B (📈 PRIORITY 2): Trend-following option contract assignment.
  Converts BOTH fresh breakout triggers and established trend states to trades.
===============================================================================
"""

import pandas as pd
from datetime import datetime
from zoneinfo import ZoneInfo
import traceback  # 🛠️ For tracing silent execution loop failures
from syscnfgpxy import TICKER

# Ingestion gateways from your exact strategy matrix modules
from sysmktpxy import get_signal, CHECK_CONFIRMED_ONLY
from sysstrndpxy import calculate_supertrend
from sysbbospxy import get_bos_bar  # Ingesting your 42-min structural breakout engine

def get_entry_signal(df=None):
    """
    Master Router with Deep Telemetry Monitoring.
    """
    print("\n" + "🔍 DEBUG START: INITIALIZING ROUTER SCAN 🔍".center(60, "═"))
    
    # 1. DATA SYNCHRONIZATION AND MULTI-INDEX HEADER FLATTENING
    if df is None or df.empty:
        print("💡 Dataframe empty or None. Fetching fresh 5-day continuous stream buffer from yfinance...")
        import yfinance as yf
        ticker_obj = yf.Ticker(TICKER)
        df = ticker_obj.history(period="5d", interval="1m")
        print(f"📦 Successfully downloaded data matrix. Shape: {df.shape}")
        
    if df.empty:
        print("❌ CRITICAL: Data stream returned an empty dataframe from yfinance framework.")
        return "NONE", "NONE"
        
    master_df = df.copy()
    
    # Clean up multi-index column structures safely to avoid quiet KeyError failures
    if isinstance(master_df.columns, pd.MultiIndex):
        print("🛠️ MultiIndex column detected. Flattening columns to avoid KeyError loops...")
        master_df.columns = master_df.columns.get_level_values(0)

    # 2. SEGREGATED INGESTION FLOW VIA INDEPENDENT PIPES
    print("📡 Pulling execution states from strategy pipes...")
    try:
        _, exit_sig = get_signal(master_df)
        exit_sig = str(exit_sig).upper().strip()
        print(f"  -> [sysmktpxy] Raw Exit Signal: '{exit_sig}'")
    except Exception as e:
        print(f"  ❌ ERROR inside sysmktpxy pipeline: {e}")
        exit_sig = "NONE"

    try:
        _, bos_signal = get_bos_bar(master_df)
        bos_signal = str(bos_signal).upper().strip()
        print(f"  -> [sysbbospxy] Raw BOS Breakout Signal: '{bos_signal}'")
    except Exception as e:
        print(f"  ❌ ERROR inside sysbbospxy pipeline: {e}")
        bos_signal = "NONE"

    print("📊 Evaluating sysstrndpxy 10:3 supertrend matrices...")
    strnd_df = calculate_supertrend(master_df)
    
    strnd_signal = "NONE"
    strnd_trend = "NEUTRAL"

    if strnd_df is not None and not strnd_df.empty:
        idx = -2 if CHECK_CONFIRMED_ONLY else -1
        print(f"  -> Target lookup row index: {idx} (CHECK_CONFIRMED_ONLY: {CHECK_CONFIRMED_ONLY})")
        try:
            strnd_signal = str(strnd_df.iloc[idx]['st_signal_full']).upper().strip()
            strnd_trend  = str(strnd_df.iloc[idx]['st_trend_full']).upper().strip()
            print(f"  -> [sysstrndpxy] Signal Field: '{strnd_signal}' | Trend Field: '{strnd_trend}'")
        except Exception as e:
            print(f"  ❌ ERROR parsing sysstrndpxy array columns: {e}")
            print(traceback.format_exc())
    else:
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

    print(f"⏰ Synchronized IST Execution Time: {current_time_ist.strftime('%H:%M:%S')}")
    print(f"🔓 Market Window Threshold Locks: Open={market_open} | Boundary={time_boundary}")

    final_signal = "NONE"

    # 4. IST TIME-BASED OPTIONS ROUTING ENGINE
    if market_open <= current_time_ist < time_boundary:
        print("🌅 CURRENT TIMING STATE: Early Morning opening window logic active.")
        if exit_sig == "BUY":
            final_signal = "ATMBUY"
        elif exit_sig == "SELL":
            final_signal = "ATMSELL"
        else:
            final_signal = "NONE"
    else:
        print("🏙️ CURRENT TIMING STATE: Standard Continuous continuous window logic active.")
        print(f"🛡️ STEP 1: Testing Priority 1 Breakouts (bos_signal == '{bos_signal}')...")
        
        # 👑 👑 👑 PRIORITY 1: High-Volume 42-Min Structural Breakouts (sysbbospxy) OVERRULE
        if bos_signal == "BUY":
            print("  🏆 PRIORITY 1 UNLOCKED: Bullish BOS Structural Breakout confirmed.")
            final_signal = "ATMBUY"
        elif bos_signal == "SELL":
            print("  🏆 PRIORITY 1 UNLOCKED: Bearish BOS Structural Breakdown confirmed.")
            final_signal = "ATMSELL"
            
        # 📈 PRIORITY 2: Direct Upstream-Filtered Action Gates 
        else:
            print(f"  ↳ Priority 1 is 'NONE'. Falling down to Step 2: Testing Priority 2 (signal='{strnd_signal}', trend='{strnd_trend}')...")
            
            # Diagnostic evaluation logs to map out why the 'and' statement fails
            cond_buy = (strnd_signal == "BUY" and strnd_trend == "BULL")
            cond_sell = (strnd_signal == "SELL" and strnd_trend == "BEAR")
            print(f"    - Testing Condition Call (BUY and BULL): {cond_buy}")
            print(f"    - Testing Condition Put (SELL and BEAR): {cond_sell}")
            
            if strnd_signal == "BUY" and strnd_trend == "BULL":
                print("  🚀 PRIORITY 2 UNLOCKED: Dynamic Breakout Switch approved.")
                final_signal = "ATMBUY"
            elif strnd_signal == "SELL" and strnd_trend == "BEAR":
                print("  🚀 PRIORITY 2 UNLOCKED: Dynamic Breakdown Switch approved.")
                final_signal = "ATMSELL"
            else:
                print("    ❌ All Priority Entry condition gates failed to match parameters.")
                final_signal = "NONE"

    # 5. OPTIMIZED TELEMETRY ALERT ENGINE
    print(f"🏁 FINAL ROUTING ENGINE DECISION VALUE: '{final_signal}'")
    if final_signal in ["ATMBUY", "ATMSELL", "OTMBUY", "OTMSELL"]:
        print(f"⏰ [IST: {current_time_ist.strftime('%H:%M:%S')}] 🔥 ACTION-{final_signal} 🔥 ".center(40))

    print("═" * 43 + "\n")
    return final_signal, exit_sig

if __name__ == "__main__":
    print("\n[PXY ROUTER STATUS] Upstream Filtered Option Route Matrix Active.")
    print("-" * 50)
    final_route, raw_exit = get_entry_signal(df=None)
    print("-" * 50)
    print(f"FINAL DECISION >> ROUTE STATUS: {final_route} | RAW EXIT FROM MKT: {raw_exit}")
