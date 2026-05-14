# sysmktpxy.py
"""
===============================================================================
PXY GEOMETRIC ENGINE CORE SYSTEM DOCUMENTATION MASTER INDEX
===============================================================================
PART 1: RAW CANDLESTICK BASE STATES (UNFILTERED)
1. Bullish Reversal Rebound State (BUY)       - Formula: (C1 < O1) AND (C0 > O0)
2. Bullish Trend Continuation State (BULL)    - Formula: (C1 > O1) AND (C0 > O0)
3. Bearish Reversal Breakdown State (SELL)    - Formula: (C1 > O1) AND (C0 < O0)
4. Bearish Trend Continuation State (BEAR)    - Formula: (C1 < O1) AND (C0 < O0)
5. Equilibrium Flat Market State (NONE)       - Formula: (C0 == O0)

PART 2: FILTERED SYSTEM EXECUTION ENGINE LABELS
1. CROSSBUY  - Fired on the exact candle that closes ABOVE the SuperTrend line.
2. CROSSSELL - Fired on the exact candle that closes BELOW the SuperTrend line.
3. TRENDBUY  - Pullback Reversal entry formed while price is already ABOVE SuperTrend.
4. TRENDSELL - Pullback Reversal entry formed while price is already BELOW SuperTrend.
5. BULL      - Neutral Bullish tracking state; no new entry execution allowed.
6. BEAR      - Neutral Bearish tracking state; no new entry execution allowed.
===============================================================================
"""

import numpy as np
import pandas as pd
import json
import os
from datetime import datetime
from sysdtafpxy import fetch_yf_data
from sysstrndpxy import calculate_supertrend

# Global Config
DEBUG = True

def _print_console_bar(st, c2, c1, c0, o2, o1, o0, cross_up, cross_dn, entry, exit_sig):
    """
    Renders the graphical sorted ASCII price matrix layout inside the console terminal.
    Dynamically tracks the relative positions of structural prices against the SuperTrend line.
    """
    # ANSI escape code constants
    RST = "\033[0m"          # Reset Color
    RED = "\033[91m"          # Red for Bearish/ST
    GRN = "\033[92m"          # Green for Bullish
    YLW = "\033[1;93m"        # Bold Yellow for Highlight/Trend
    GRAY = "\033[90m"         # Dim Gray for layout lines

    min_val = min(c2, c1, c0, st) - 2
    max_val = max(c2, c1, c0, st) + 2
    scale_width = 20

    def get_clean_bar(val, marker="█"):
        pos = int(((val - min_val) / (max_val - min_val)) * scale_width)
        pos = max(1, pos)
        return (marker * pos).ljust(scale_width)

    # Contextual settings
    trend_str = "BULL" if c0 >= st else "BEAR"
    trend_color = GRN if c0 >= st else RED
    diff_val = c0 - st

    # Contextual candle coloring evaluation logic based on Open arrays
    c2_color = GRN if c2 >= o2 else RED
    c1_color = GRN if c1 >= o1 else RED
    c0_color = GRN if c0 >= o0 else RED

    # Build row items for descending sort logic (highest price on top)
    rows = [
        (st, f"ST-{st:.2f}", "-", RED),
        (c2, f"C2-{c2:.2f}", "█", c2_color),
        (c1, f"C1-{c1:.2f}", "█", c1_color),
        (c0, f"C0-{c0:.2f}", "█", c0_color)
    ]
    rows.sort(key=lambda item: item[0], reverse=True)

    print(f"\n{YLW}=== GEOMETRIC ENGINE CONSOLE MONITOR ==={RST}")
    for val, label, marker, color in rows:
        print(f"{color}{label}{RST} : {GRAY}[{color}{get_clean_bar(val, marker)}{GRAY}]{RST}")
    print(f"{YLW}========================================{RST}")
    print(f"UP:{YLW}{str(cross_up)}{RST} | DDN:{YLW}{str(cross_dn)}{RST} | Trnd:{trend_color}{trend_str}{RST} ({diff_val:+.2f})")
    print(f"ENTRY: {YLW}{entry}{RST} | EXIT: {YLW}{exit_sig}{RST}")

def log_sync_state(timestamp, entry, exit_sig, price, st):
    """
    Logs the synchronized system state variables into a local rolling JSON buffer.
    Maintains a maximum lookback history of exactly 100 entries inside ~/pxy/tv_sync_log.json.
    """
    try:
        dir_path = os.path.expanduser("~/pxy")
        os.makedirs(dir_path, exist_ok=True)
        file_path = os.path.join(dir_path, "tv_sync_log.json")

        log_entry = {
            "Timestamp": str(timestamp),
            "Price": float(price),
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
                except Exception:
                    logs = []

        logs.append(log_entry)
        with open(file_path, "w") as f:
            json.dump(logs[-100:], f, indent=4)
    except Exception as e:
        if DEBUG:
            print(f"Logger Engine Exception Encountered: {e}")

def get_signal(df=None):
    """
    Main signal generation function. Handles raw matrix ingestion, extracts positional vectors, 
    processes candlestick patterns, and routes them through decoupled trend filters.
    """
    if df is None:
        df = fetch_yf_data()
        
    if df is None or df.empty:
        return "NONE", "NONE"

    try:
        # --- 1. RUN STRUCTURAL SUPERTREND BACKBONE ---
        df_calc = calculate_supertrend(df)

        # --- 2. SIGNAL MATRIX LOOKBACK SHIFTS (OPEN, CLOSE, AND ST LINES) ---
        df_calc['c1'] = df_calc['Close'].shift(1)
        df_calc['c2'] = df_calc['Close'].shift(2)
        df_calc['o1'] = df_calc['Open'].shift(1)
        df_calc['o2'] = df_calc['Open'].shift(2)
        df_calc['st1'] = df_calc['ST'].shift(1)
        
        df_calc['aboveBlack'] = df_calc['Close'] > df_calc['ST']
        df_calc['belowBlack'] = df_calc['Close'] < df_calc['ST']
        df_calc['crossAboveBlack'] = (df_calc['c1'] <= df_calc['st1']) & (df_calc['Close'] > df_calc['ST'])
        df_calc['crossBelowBlack'] = (df_calc['c1'] >= df_calc['st1']) & (df_calc['Close'] < df_calc['ST'])

        # --- 3. ISOLATE VECTOR STATES FROM LAST ROW ---
        last_row = df_calc.iloc[-1].copy()
        c0, st0 = float(last_row['Close']), float(last_row['ST'])
        o0 = float(last_row['Open'])
        c1, c2 = float(last_row['c1']), float(last_row['c2'])
        o1, o2 = float(last_row['o1']), float(last_row['o2'])
        
        cross_up_black = bool(last_row['crossAboveBlack'])
        cross_dn_black = bool(last_row['crossBelowBlack'])
        above_black = bool(last_row['aboveBlack'])
        below_black = bool(last_row['belowBlack'])

        is_green_c0 = c0 > o0
        is_red_c0 = c0 < o0
        is_green_c1 = c1 > o1
        is_red_c1 = c1 < o1

        # --- 4. STEP 1: CALCULATE RAW INDEPENDENT EXIT TREND STATE FIRST ---
        exit_sig = "NONE"
        if is_red_c1 and is_green_c0:
            exit_sig = "BUY"
        elif is_green_c1 and is_green_c0:
            exit_sig = "BULL"
        elif is_green_c1 and is_red_c0:
            exit_sig = "SELL"
        elif is_red_c1 and is_red_c0:
            exit_sig = "BEAR"

        # --- 5. STEP 2: APPLY FILTERS DIRECTLY ON PRE-COMPUTED EXITS FOR ENTRY ---
        entry = "NONE"

        # Bullish Entry Rules Cascade Filter
        if cross_up_black:
            entry = "CROSSBUY"
        elif exit_sig == "BUY" and above_black:
            entry = "TRENDBUY"
        elif exit_sig == "BULL" and above_black:
            entry = "BULL"

        # Bearish Entry Rules Cascade Filter (Decoupled to protect crossover detection)
        if cross_dn_black:
            entry = "CROSSSELL"
        elif exit_sig == "SELL" and below_black:
            entry = "TRENDSELL"
        elif exit_sig == "BEAR" and below_black:
            entry = "BEAR"

        if DEBUG:
            _print_console_bar(st0, c2, c1, c0, o2, o1, o0, cross_up_black, cross_dn_black, entry, exit_sig)
            
        log_sync_state(df_calc.index[-1], entry, exit_sig, c0, st0)
        return entry, exit_sig

    except Exception as e:
        if DEBUG:
            print(f"PXY Master Core Error: {e}")
        return "NONE", "NONE"

if __name__ == "__main__":
    e, x = get_signal()
    print(f"\nFinal Synchronized Outputs -> Entry Status: {e} | Exit Trend: {x}")




