import warnings
import json
import os
import subprocess
import numpy as np
import pandas as pd
import yfinance as yf
from syscnfgpxy import TICKER

warnings.simplefilter(action='ignore', category=FutureWarning)

# Explicitly enforce Indian Standard Time zone mapping
TIMEZONE = 'Asia/Kolkata'

# ==========================================================================
# ⚡ EXACT PATH ALIGNMENT FOR SYS/EXE/RUN DIRECTORY STRUCTURE
# ==========================================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RUN_DIR = os.path.join(BASE_DIR, "exe", "run")

SCRIPT_PATH = os.path.join(RUN_DIR, "runnftfutpxy.py")
JSON_FILE_PATH = os.path.join(RUN_DIR, "nftfut.json")


def run_nftfut_module():
    """Executes runnftfutpxy.py directly within the sys/exe/run/ subdirectory layer."""
    if os.path.exists(SCRIPT_PATH):
        try:
            subprocess.run(
                ["python", SCRIPT_PATH], 
                cwd=RUN_DIR,
                stdout=subprocess.DEVNULL, 
                stderr=subprocess.DEVNULL, 
                check=True
            )
        except Exception:
            pass

def get_live_futures_price():
    """Reads and parses the flat price from the JSON file inside the run directory."""
    if os.path.exists(JSON_FILE_PATH):
        try:
            with open(JSON_FILE_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                return float(data.get("price", 0.0))
        except Exception:
            return 0.0
    return 0.0

def apply_ohlc_transformation(df, mode=1):
    """Executes structural, isolated mathematical transformations based on explicit modes."""
    if df.empty:
        return df

    out = df.copy()
    raw_o = df['Open'].to_numpy()
    raw_h = df['High'].to_numpy()
    raw_l = df['Low'].to_numpy()
    raw_c = df['Close'].to_numpy()

    # Mode 0: Hyper-Sensitive Modified Close Candles (Triggered if market is SIDE)
    if mode == 0:
        out['Close'] = np.where(raw_c >= raw_o, (raw_c + raw_h) / 2.0, (raw_c + raw_l) / 2.0)
        return out

    # Mode 1: Raw Candles
    elif mode == 1:
        return out

    # Mode 2: OC/2 (Triggered if market is BULL or BEAR)
    elif mode == 2:
        out['Close'] = (raw_o + raw_c) / 2.0
        return out

    # Mode 3: OCC/3
    elif mode == 3:
        out['Close'] = (raw_o + (2 * raw_c)) / 3.0
        return out

    # Mode 4: OCCC/4
    elif mode == 4:
        out['Close'] = (raw_o + (3 * raw_c)) / 4.0
        return out

    # Mode 5: OHLCC/5
    elif mode == 5:
        out['Close'] = (raw_o + raw_h + raw_l + (2 * raw_c)) / 5.0
        return out

    return out

def fetch_yf_data(period=None, interval="1m", target_rows=60):
    """Dynamic historical ingestion engine utilizing vectorized structural transformations"""
    
    # Step 0: Execute the module script and fetch the latest price from the run directory
    run_nftfut_module()
    fut_price = get_live_futures_price()

    ticker_obj = yf.Ticker(TICKER)
    df = pd.DataFrame()
    buffer_rows = target_rows + 5
    
    if period is not None:
        try:
            df = ticker_obj.history(period=period, interval=interval)
        except Exception:
            pass
            
    if df.empty:
        for search_period in ["5d", "7d", "max"]:
            try:
                df = ticker_obj.history(period=search_period, interval=interval)
                if not df.empty:
                    df.dropna(subset=['Open', 'High', 'Low', 'Close'], inplace=True)
                    if len(df) >= buffer_rows:
                        break
            except Exception:
                pass
                
    if df.empty or len(df) < buffer_rows:
        return pd.DataFrame()
        
    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index)
        
    if df.index.tz is None:
        df = df.tz_localize('UTC').tz_convert(TIMEZONE)
    else:
        df = df.tz_convert(TIMEZONE)

    # ==========================================================================
    # ⚡ CORE PRE-PROCESSING LAYER: ALL-FIELD VECTORIZED OHLC CO-AVERAGING
    # ==========================================================================
    if fut_price > 0:
        # --- VERIFICATION PRINT START ---
        print("\n" + "="*70)
        print(f"🔄 DATAFRAME INGESTION PRE-PROCESSOR")
        print(f"📥 Successfully parsed JSON tracking file: {JSON_FILE_PATH}")
        print(f"📈 Extracted Live Nifty Future Price: {fut_price:.2f}")
        print("="*70)
        print("📋 Before Co-Averaging Core Dataframe Sample (Raw Spot Data):")
        print(df[['Open', 'High', 'Low', 'Close']].tail(3))
        # ---------------------------------

        df['Open']  = (df['Open'] + fut_price) / 2.0
        df['High']  = (df['High'] + fut_price) / 2.0
        df['Low']   = (df['Low'] + fut_price) / 2.0
        df['Close'] = (df['Close'] + fut_price) / 2.0

        # --- VERIFICATION PRINT END ---
        print("\n📊 After Vectorized OHLC Co-Averaging Engine Baseline:")
        print(df[['Open', 'High', 'Low', 'Close']].tail(3))
        print("="*70 + "\n")
        # -------------------------------
    else:
        print(f"\n⚠️ Alert: JSON price validation failed or read 0.0 from {JSON_FILE_PATH}. Skipping math matrix merge.\n")
        
    # ==========================================================================
    # ⚡ LOCAL IMPORT SHIELD: Prevents Circular Dependency Faults
    # ==========================================================================
    from sysstrndpxy import get_market_trend
    
    # Step 1: Run the blended OHLC dataframe through the trend classification engine
    market_state = get_market_trend(df)
    
    # Step 2: Assign logic mode dynamically based on state output (0 for SIDE, else 2)
    dynamic_mode = 0 if market_state == 'SIDE' else 2
    
    # Step 3: Run structural transformations on the close values using the dynamic mode switch
    processed_df = apply_ohlc_transformation(df, mode=dynamic_mode)
    return processed_df.tail(target_rows)

