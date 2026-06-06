import os
import sys
import json
import warnings
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# Silence future warning constraints completely
warnings.simplefilter(action='ignore', category=FutureWarning)

# ===============================================================================
# 🛠️ INTERNAL SINGLE SOURCE OF TRUTH (SELF-SUSTAINED GLOBALS)
# ===============================================================================
TICKER = "^NSEI"           # Nifty 50 Index default
TIMEZONE = "Asia/Kolkata"  # Indian Standard Time (IST)

def run_independent_engine():
    """Main self-sustained engine process block fetching exactly 1 full day of 1m data"""
    tz_ist = ZoneInfo(TIMEZONE)
    
    # 🟢 DYNAMIC DAY RESOLUTION: Calculate explicit 24-hour window boundaries for today
    today = datetime.now(tz_ist)
    
    # Format absolute explicit timestamp limits for the yfinance engine
    start_date_str = today.strftime("%Y-%m-%d")
    # Add 1 day forward to the end date parameter to guarantee yfinance absorbs the full day
    end_date_str = (today + timedelta(days=1)).strftime("%Y-%m-%d")
    
    ticker_obj = yf.Ticker(TICKER)
    interval = "1m"    # 1-minute interval bars

    try:
        # Fetch absolute raw fast info/history using explicit point-in-time constraints
        raw_data = ticker_obj.history(start=start_date_str, end=end_date_str, interval=interval)
        
        # 💡 FALLBACK: If market hasn't opened today or it's a weekend, pull the last valid session
        if raw_data.empty:
            if datetime.now(tz_ist).weekday() >= 5: # Weekend Check
                print("📋 Weekend/Holiday detected. Pulling most recent full historical session...")
            raw_data = ticker_obj.history(period="1d", interval=interval)

        if not raw_data.empty:
            # Force timestamp index conversion to IST before dumping
            if not isinstance(raw_data.index, pd.DatetimeIndex):
                raw_data.index = pd.to_datetime(raw_data.index)
            if raw_data.index.tz is None:
                raw_data = raw_data.tz_localize('UTC').tz_convert(TIMEZONE)
            else:
                raw_data = raw_data.tz_convert(TIMEZONE)

            # Setup paths safely by targeting the string index 0 from splitext tuple
            script_directory = os.path.dirname(os.path.abspath(__file__)) if '__file__' in locals() else os.getcwd()
            parent_directory = os.path.dirname(script_directory)
            base_name = os.path.splitext(os.path.basename(__file__))[0] if '__file__' in locals() else "sysddmppxy"
            target_export_path = os.path.join(parent_directory, f"{base_name}.json")
            
            # Dump whole data block to JSON with IST timestamps
            raw_data.to_json(target_export_path, date_format='iso', orient='split')
            print("📦 RAW JSON DUMP SUCCESS (IST)")
            
            processed_df = raw_data.copy()
            print(f"✅ ENGINE SUCCESS | Pure Raw Rows Collected: {len(processed_df)}")
            return processed_df
            
        else:
            print("WARNING: Raw data fetch returned empty frame. Skipping JSON dump.")
    except Exception as e:
        print(f"RAW_JSON_DUMP_ERROR | {e}")
    
    return pd.DataFrame()

if __name__ == "__main__":
    run_independent_engine()

