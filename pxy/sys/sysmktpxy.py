# sysmktpxy.py
import numpy as np
import pandas as pd
import json
import os
from datetime import datetime
from sysdtafpxy import fetch_yf_data
from sysstrndpxy import calculate_supertrend  # Uses your upgraded TSMA(42) + Price Midpoint architecture

DEBUG = True

def calc_tsma_np(series, window=7):
    """Pure NumPy Linear Regression Matching Pine Script's ta.linreg"""
    if len(series) < window:
        window = len(series)
    y = series.tail(window).values
    x = np.arange(len(y))
    coeffs = np.polyfit(x, y, 1)
    return float(coeffs[0] * (len(y) - 1) + coeffs[1])

def log_sync_state(timestamp, entry, exit_sig, price, tsma, st):
    try:
        dir_path = os.path.expanduser("~/pxy")
        os.makedirs(dir_path, exist_ok=True)
        file_path = os.path.join(dir_path, "tv_sync_log.json")
        log_entry = {
            "Timestamp": str(timestamp),
            "Price": float(price),
            "TSMA": round(float(tsma), 2),
            "ST_Line": round(float(st), 2),
            "Signal_Entry": str(entry),
            "Signal_Exit": str(exit_sig),
            "Logged_At": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        logs = []
        if os.path.exists(file_path):
            with open(file_path, "r") as f:
                try:
                    logs = json.load(f)
                except:
                    logs = []
        logs.append(log_entry)
        with open(file_path, "w") as f:
            json.dump(logs[-100:], f, indent=4)
    except:
        pass

def get_signal(df=None):
    if df is None:
        df = fetch_yf_data()
    if df is None or df.empty:
        return "NONE", "NONE"
        
    try:
        # --- 1. RUN STRUCTURAL SUPERTREND BACKBONE ---
        df_calc = calculate_supertrend(df) # Slices to a strict 50-row matrix internally
        
        # --- 2. EXTRACT MATURED PRICE SERIE COMPONENTS ---
        c_s = df_calc['Close']
        
        # --- 3. CALC FAST TSMA_7 TRACKER VECTORS ---
        tsma_list = [calc_tsma_np(c_s.iloc[:i+1], 7) if (i >= 1) else float(c_s.iloc[i]) for i in range(len(df_calc))]
        df_calc['tsma_7'] = tsma_list
        
        # --- 4. SIGNAL MATRIX LOOKBACK SHIFTS (STRICT C0, C1, C2 ONLY) ---
        df_calc['c1'] = df_calc['Close'].shift(1)
        df_calc['c2'] = df_calc['Close'].shift(2)
        df_calc['tsma1'] = df_calc['tsma_7'].shift(1)
        df_calc['st1'] = df_calc['ST'].shift(1)
        
        df_calc['aboveBlack'] = df_calc['Close'] > df_calc['ST']
        df_calc['belowBlack'] = df_calc['Close'] < df_calc['ST']
        
        df_calc['crossAboveBlack'] = (df_calc['c1'] <= df_calc['st1']) & (df_calc['Close'] > df_calc['ST'])
        df_calc['crossBelowBlack'] = (df_calc['c1'] >= df_calc['st1']) & (df_calc['Close'] < df_calc['ST'])
        
        # --- 5. ISOLATE VECTOR STATES FROM LAST ROW ---
        last_row = df_calc.iloc[-1].copy()
        c0, tsma0, st0 = float(last_row['Close']), float(last_row['tsma_7']), float(last_row['ST'])
        c1, c2 = float(last_row['c1']), float(last_row['c2'])
        cross_up_black = bool(last_row['crossAboveBlack'])
        cross_dn_black = bool(last_row['crossBelowBlack'])
        
        # Core Geometric Formations (C0, C1, C2 Only)
        v_pattern_up = (c1 < c2) and (c0 > c1)
        inverted_v_down = (c1 > c2) and (c0 < c1)
        
        three_candles_up = (c0 > c1) and (c1 > c2)
        three_candles_down = (c0 < c1) and (c1 < c2)
        
        st_signal = str(last_row['ST_Trend']) 
        above_black = bool(last_row['aboveBlack'])
        below_black = bool(last_row['belowBlack'])
        
        if DEBUG:
            print(f"\n--- PXY DEBUG (GEOMETRIC ENGINE) --- Price: {c0} | TSMA: {tsma0:.2f} | ST: {st0:.2f}")
            print(f"Candle Context : C0: {c0} | C1: {c1} | C2: {c2}")

        # --- 6. ENTRY SIGNAL EXECUTION ENGINE ---
        entry = "NONE"
        if st_signal == "BUY" or cross_up_black:
            entry = "BUY"
        elif st_signal == "SELL" or cross_dn_black:
            entry = "SELL"
        elif v_pattern_up and above_black:
            entry = "BUY"
        elif inverted_v_down and below_black:
            entry = "SELL"
        elif three_candles_up and above_black and (c0 > tsma0):
            entry = "BULL"
        elif three_candles_down and below_black and (c0 < tsma0):
            entry = "BEAR"

        # --- 7. EXIT SIGNAL ENGINE (FIXED - NO EXTERNAL LAYER CONDITIONS) ---
        # Evaluates trend exhaustion strictly using the structural patterns
        exit_sig = "SIDE"
        if inverted_v_down or three_candles_down:
            exit_sig = "SELL"  # Signal exit to flatten long setups
        elif v_pattern_up or three_candles_up:
            exit_sig = "BUY"   # Signal exit to flatten short setups
            
        log_sync_state(df_calc.index[-1], entry, exit_sig, c0, tsma0, st0)
        return entry, exit_sig
        
    except Exception as e:
        if DEBUG:
            print(f"PXY Master Core Error: {e}")
        return "NONE", "NONE"

if __name__ == "__main__":
    e, x = get_signal()
    print(f"Final Synchronized Outputs -> Entry Status: {e} | Exit Trend: {x}")


