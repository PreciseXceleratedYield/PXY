import os
import sys
import json
import warnings
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from syscnfgpxy import (
    SYSCNFGPXY_TICKER,
    SYSCNFGPXY_TIMEZONE,
    SYSDTAFPXY_DEFAULT_INTERVAL,
)
from sysmodepxy import dispatch_mode

# Silence future warning constraints completely
warnings.simplefilter(action='ignore', category=FutureWarning)

# ===============================================================================
# 🛠️ INTERNAL SINGLE SOURCE OF TRUTH (SELF-SUSTAINED GLOBALS)
# ===============================================================================
def _run_independent_engine_production():
    """
    Main self-sustained engine process block.
    Dumps exactly 1 day of 1m data using strict today logic with an
    automatic fallback to the most recent historical session available.
    """
    tz_ist = ZoneInfo(str(SYSCNFGPXY_TIMEZONE))
    today = datetime.now(tz_ist)
    
    # 🟢 STEP 1: Attempt strict date-bracket lookup for today's session
    start_date_str = today.strftime("%Y-%m-%d")
    end_date_str = (today + timedelta(days=1)).strftime("%Y-%m-%d")
    
    interval = SYSDTAFPXY_DEFAULT_INTERVAL

    try:
        ticker_obj = yf.Ticker(SYSCNFGPXY_TICKER)
        # Fast point-in-time lookup block
        raw_data = ticker_obj.history(start=start_date_str, end=end_date_str, interval=interval)

        # 🟢 STEP 2: FALLBACK MECHANISM — Pull latest session if today is empty
        if raw_data.empty:
            print("📋 Today's data empty (Weekend/Holiday/Pre-Market). Fetching latest available session...")
            raw_data = ticker_obj.history(period="1d", interval=interval)

        if not raw_data.empty:
            # 🟢 STEP 3: FORCE 100% UNIFORM IST TIMESTAMPS
            if not isinstance(raw_data.index, pd.DatetimeIndex):
                raw_data.index = pd.to_datetime(raw_data.index)
            if raw_data.index.tz is None:
                raw_data = raw_data.tz_localize('UTC').tz_convert(SYSCNFGPXY_TIMEZONE)
            else:
                raw_data = raw_data.tz_convert(SYSCNFGPXY_TIMEZONE)

            # 🟢 STEP 4: RESOLVE PRODUCTION DUMP DIRECTORIES (UPDATED TO PARENT'S OTHER CHILD 'WEB' DIR)
            script_directory = os.path.dirname(os.path.abspath(__file__)) if '__file__' in locals() else os.getcwd()
            parent_directory = os.path.dirname(script_directory)
            
            # Target the parallel 'web' sibling directory
            target_web_directory = os.path.join(parent_directory, "web")
            os.makedirs(target_web_directory, exist_ok=True)
            
            target_export_path = os.path.join(target_web_directory, "webdaypxy.json")
            
            # 🟢 STEP 5: DUMP ENTIRE RAW COMPONENT DATA MATRIX
            raw_data.to_json(target_export_path, date_format='iso', orient='split')
            print("📦 RAW JSON DUMP SUCCESS (IST)")
            
            processed_df = raw_data.copy()
            print(f"✅ ENGINE SUCCESS | Session Rows Saved: {len(processed_df)}")
            return processed_df
            
        else:
            print("CRITICAL: Failed to retrieve data from yfinance server pool.")
    except Exception as e:
        print(f"RAW_JSON_DUMP_ERROR | {e}")
    
    return pd.DataFrame()


def run_independent_engine():
    return dispatch_mode("run_independent_engine", _run_independent_engine_production)


if __name__ == "__main__":
    run_independent_engine()
