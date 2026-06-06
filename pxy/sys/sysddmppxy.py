import os
import sys
import json
import warnings
import pandas as pd
import yfinance as yf
from datetime import datetime
from zoneinfo import ZoneInfo

# Silence future warning constraints completely
warnings.simplefilter(action='ignore', category=FutureWarning)

# ===============================================================================
# 🛠️ INTERNAL SINGLE SOURCE OF TRUTH (SELF-SUSTAINED GLOBALS)
# ===============================================================================
TICKER = "^NSEI"           # Nifty 50 Index default
TIMEZONE = "Asia/Kolkata"  # Indian Standard Time (IST)
TARGET_ROWS = 60           # Data frame trailing tail count

def run_independent_engine():
    """Main self-sustained engine process block utilizing pure raw close data with no time locks"""
    ticker_obj = yf.Ticker(TICKER)
    period = "5d"
    interval = "1m"

    try:
        # Fetch absolute raw fast info/history instantly on execution
        raw_data = ticker_obj.history(period=period, interval=interval)
        
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
            base_name = os.path.splitext(os.path.basename(__file__))[0] if '__file__' in locals() else "sysdtafpxy"
            target_export_path = os.path.join(parent_directory, f"{base_name}.json")
            
            # Dump whole data block to JSON with IST timestamps
            raw_data.to_json(target_export_path, date_format='iso', orient='split')
            print("📦 RAW JSON DUMP SUCCESS (IST)")
            
            # Slices required sizing parameters internally using pure raw closing prices
            processed_df = raw_data.tail(TARGET_ROWS).copy()
            print(f"✅ ENGINE SUCCESS | Pure Raw Rows Collected: {len(processed_df)}")
            return processed_df
            
        else:
            print("WARNING: Raw data fetch returned empty frame. Skipping JSON dump.")
    except Exception as e:
        print(f"RAW_JSON_DUMP_ERROR | {e}")
    
    return pd.DataFrame()

if __name__ == "__main__":
    run_independent_engine()
