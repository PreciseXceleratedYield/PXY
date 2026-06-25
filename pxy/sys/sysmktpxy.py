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
===============================================================================
"""

import numpy as np
import pandas as pd
import json
import os
from datetime import datetime
from sysdtafpxy import fetch_yf_data

# Global Config
DEBUG = True

def _print_console_bar(c2, c1, c0, o2, o1, o0, entry, exit_sig):
    """
    Renders the graphical sorted ASCII price matrix layout inside the console terminal.
    Dynamically tracks the relative positions of structural prices.
    """
    # ANSI escape code constants
    RST = "\033[0m"          # Reset Color
    RED = "\033[91m"          # Red for Bearish
    GRN = "\033[92m"          # Green for Bullish
    YLW = "\033[1;93m"        # Bold Yellow for Highlight/Trend
    GRAY = "\033[90m"         # Dim Gray for layout lines

    min_val = min(c2, c1, c0) - 2
    max_val = max(c2, c1, c0) + 2
    scale_width = 20

    def get_clean_bar(val, marker="█"):
        pos = int(((val - min_val) / (max_val - min_val)) * scale_width) if max_val != min_val else 1
        pos = max(1, pos)
        return (marker * pos).ljust(scale_width)

    # Contextual candle coloring evaluation logic based on Open arrays
    c2_color = GRN if c2 >= o2 else RED
    c1_color = GRN if c1 >= o1 else RED
    c0_color = GRN if c0 >= o0 else RED

    # Build row items for descending sort logic (highest price on top)
    rows = [
        (c2, f"C2-{c2:.2f}", "█", c2_color),
        (c1, f"C1-{c1:.2f}", "█", c1_color),
        (c0, f"C0-{c0:.2f}", "█", c0_color)
    ]
    rows.sort(key=lambda item: item[0], reverse=True)

    print(f"\n{YLW}=== GEOMETRIC ENGINE CONSOLE MONITOR ==={RST}")
    for val, label, marker, color in rows:
        print(f"{color}{label}{RST} : {GRAY}[{color}{get_clean_bar(val, marker)}{GRAY}]{RST}")
    print(f"{YLW}========================================{RST}")
    print(f"       ENTRY (CONFIRMED): {YLW}{entry}{RST} | EXIT (RUNNING): {YLW}{exit_sig}{RST}")

def log_sync_state(timestamp, entry, exit_sig, price):
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
    Main signal generation function. Decoupled into two separate streams:
    - ENTRY pipeline evaluates the last completely CONFIRMED candle (Index -2)
    - EXIT pipeline evaluates the live, active RUNNING candle (Index -1)
    """
    if df is None:
        df = fetch_yf_data()
        
    if df is None or len(df) < 3:
        return "NONE", "NONE"

    try:
        # --- 1. EXTRACT GEOMETRY FOR THE LIVE RUNNING CANDLE PIPELINE (INDEX -1) ---
        run_row = df.iloc[-1]
        run_prev_row = df.iloc[-2]
        
        c0_run, o0_run = float(run_row['Close']), float(run_row['Open'])
        c1_run, o1_run = float(run_prev_row['Close']), float(run_prev_row['Open'])
        
        # --- 2. EXTRACT GEOMETRY FOR THE CONFIRMED CANDLE PIPELINE (INDEX -2) ---
        conf_row = df.iloc[-2]
        conf_prev_row = df.iloc[-3]
        
        c0_conf, o0_conf = float(conf_row['Close']), float(conf_row['Open'])
        c1_conf, o1_conf = float(conf_prev_row['Close']), float(conf_prev_row['Open'])

        # --- 3. CALCULATE EXIT SIGNAL STREAM (RUNNING PIPELINE) ---
        exit_sig = "NONE"
        if c1_run < o1_run and c0_run > o0_run:
            exit_sig = "BUY"
        elif c1_run > o1_run and c0_run > o0_run:
            exit_sig = "BULL"
        elif c1_run > o1_run and c0_run < o0_run:
            exit_sig = "SELL"
        elif c1_run < o1_run and c0_run < o0_run:
            exit_sig = "BEAR"

        # --- 4. CALCULATE ENTRY SIGNAL STREAM (CONFIRMED PIPELINE) ---
        entry = "NONE"
        if c1_conf < o1_conf and c0_conf > o0_conf:
            entry = "BUY"
        elif c1_conf > o1_conf and c0_conf > o0_conf:
            entry = "BULL"
        elif c1_conf > o1_conf and c0_conf < o0_conf:
            entry = "SELL"
        elif c1_conf < o1_conf and c0_conf < o0_conf:
            entry = "BEAR"

        # --- 5. HOUSEKEEPING & LOGGING VARIABLES ---
        c2 = float(df.iloc[-3]['Close'])
        o2 = float(df.iloc[-3]['Open'])

        if DEBUG:
            _print_console_bar(c2, c1_run, c0_run, o2, o1_run, o0_run, entry, exit_sig)
            
        log_sync_state(df.index[-1], entry, exit_sig, c0_run)
        
        return entry, exit_sig

    except Exception as e:
        if DEBUG:
            print(f"Signal Processing Engine Exception: {e}")
        return "NONE", "NONE"


