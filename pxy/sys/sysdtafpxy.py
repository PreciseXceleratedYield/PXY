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
JSON_FILE_PATH = "nftfut.json"

def run_nftfut_module():
    """Executes the runnftfutpxy.py script to fetch the freshest live contract price."""
    script_path = os.path.join("exe", "run", "runnftfutpxy.py")
    if os.path.exists(script_path):
        try:
            # Executes script and suppresses verbose output to maintain a single-line clean environment
            subprocess.run(["python", script_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        except Exception:
            pass

def get_live_futures_price():
    """Reads and returns the flat price from the overwritten JSON tracking file."""
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

    # ⚡ Mode 0: Hyper-Sensitive Modified Close Candles (Triggered if market is SIDE)
    if mode == 0:
        out['Close'] = np.where(raw_c >= raw_o, (raw_c + raw_h) / 2.0, (raw_c + raw_l) / 2.0)
        return out

    # ⚡ Mode 1: Raw Candles
    elif mode == 1:
        return out

    # ⚡ Mode 2: OC/2 (Triggered if market is BULL or BEAR)
    elif mode == 2:
        out['Close'] = (raw_o + raw_c) / 2.0
        return out

    # ⚡ Mode 3: OCC/3
    elif mode == 3:
        out['Close'] = (raw_o + (2 * raw_c)) / 3.0
        return out

    # ⚡ Mode 4: OCCC/4
    elif mode == 4:
        out['Close'] = (raw_o + (3 * raw_c)) / 4.0
        return out

    # ⚡ Mode 5: OHLCC/5
    elif mode == 5:
        out['Close'] = (raw_o + raw_h + raw_l + (2 * raw_c)) / 5.0
        return out

    return out

def fetch_yf_data(period=None, interval="1m", target_rows=60):
    """Dynamic historical ingestion engine utilizing vectorized structural transformations"""
    
    # Step 0: Run the external futures proxy module and grab the exact price value
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
    # CRITICAL: This is the very first programmatic action executed on the data.
    # Blends all four spatial candle matrices with the target future baseline.
    if fut_price > 0:
        df['Open']  = (df['Open'] + fut_price) / 2.0
        df['High']  = (df['High'] + fut_price) / 2.0
        df['Low']   = (df['Low'] + fut_price) / 2.0
        df['Close'] = (df['Close'] + fut_price) / 2.0
        
    # ==========================================================================
    # ⚡ LOCAL IMPORT SHIELD: Prevents Circular Dependency Faults
    # ==========================================================================
    from sysstrndpxy import get_market_trend
    
    # Step 1: Run the newly created blended OHLC series through the structural categorizer
    market_state = get_market_trend(df)
    
    # Step 2: Assign logic mode dynamically based on state output (0 for SIDE, else 2)
    dynamic_mode = 0 if market_state == 'SIDE' else 2
    
    # Step 3: Transform final custom mathematical parameters using the dynamic mode selection
    processed_df = apply_ohlc_transformation(df, mode=dynamic_mode)
    return processed_df.tail(target_rows)

