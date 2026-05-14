# sysmktpxy.py
"""
===============================================================================
PXY GEOMETRIC ENGINE CORE SYSTEM DOCUMENTATION MASTER INDEX
===============================================================================

PART 1: RAW CANDLESTICK BASE STATES (UNFILTERED)
1. Bullish Reversal Rebound State (BUY)
   - Formula: (C1 < O1) AND (C0 > O0)
   - Meaning: Bearish drop hitting structural exhaustion and flipping up.
2. Bullish Trend Continuation State (BULL)
   - Formula: (C1 > O1) AND (C0 > O0)
   - Meaning: Persistent buyers retaining control, extending the upward leg.
3. Bearish Reversal Breakdown State (SELL)
   - Formula: (C1 > O1) AND (C0 < O0)
   - Meaning: Bullish ascent hitting resistance, forcing a downward rotation.
4. Bearish Trend Continuation State (BEAR)
   - Formula: (C1 < O1) AND (C0 < O0)
   - Meaning: Persistent distribution remaining active, cascading price lower.
5. Equilibrium Flat Market State (NONE)
   - Formula: (C0 == O0)
   - Meaning: Total doji matrix compression; no measurable directional delta.

PART 2: EXIT SIGNAL MAPPING ENGINE (exit_sig)
6. Primary Exit Rebound Trigger (exit_sig = "BUY")
   - Met: Validates State #1 (BUY). Evaluated independently of the ST line.
7. Secondary Exit Extension Trigger (exit_sig = "BULL")
   - Met: Validates State #2 (BULL). Marks active bullish continuation.
8. Primary Exit Breakdown Trigger (exit_sig = "SELL")
   - Met: Validates State #3 (SELL). Forces immediate long exit protection.
9. Secondary Exit Extension Trigger (exit_sig = "BEAR")
   - Met: Validates State #4 (BEAR). Marks active bearish continuation.
10. Neutral Exit Quiet Trigger (exit_sig = "NONE")
    - Met: Validates State #5 (NONE). System remains in holding pattern.

PART 3: ENTRY SIGNAL EXECUTION ENGINE (entry)
11. Bullish Breakout Crossover Entry (entry = "BUY")
    - Formula: (C1 <= ST1) AND (C0 > ST0) [Highest System Priority Override]
12. Bullish Reversal Filtered Entry (entry = "BUY")
    - Formula: (exit_sig == "BUY") AND (C0 > ST0)
13. Bullish Follow-Through Entry (entry = "BULL")
    - Formula: (exit_sig == "BULL") AND (C0 > ST0)
14. Bearish Breakdown Crossunder Entry (entry = "SELL")
    - Formula: (C1 >= ST1) AND (C0 < ST0) [Highest System Priority Override]
15. Bearish Reversal Filtered Entry (entry = "SELL")
    - Formula: (exit_sig == "SELL") AND (C0 < ST0)
16. Bearish Follow-Through Entry (entry = "BEAR")
    - Formula: (exit_sig == "BEAR") AND (C0 < ST0)
17. Blocked Entry Protection Safe State (entry = "NONE")
    - Formula: Patterns triggering on the wrong side of market structure.
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

def _print_console_bar(st, c2, c1, c0, cross_up, cross_dn, entry, exit_sig):
    """Helper engine function to render the graphical sorted ascii layout matrix inside the console."""
    # ANSI escape code constants
    RST = "\033[0m"       # Reset Color
    RED = "\033[91m"      # Red for ST
    GRN = "\033[92m"      # Green for Candle Closes
    YLW = "\033[1;93m"    # Bold Yellow for Highlight/Trend
    GRAY = "\033[90m"     # Dim Gray for layout lines

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

    # Build row items for descending sort logic (highest price on top)
    rows = [
        (st, f"ST-{st:.2f}", "-", RED),
        (c2, f"C2-{c2:.2f}", "█", GRN),
        (c1, f"C1-{c1:.2f}", "█", GRN),
        (c0, f"C0-{c0:.2f}", "█", GRN)
    ]
    rows.sort(key=lambda item: item, reverse=True)

    print(f"\n{YLW}=== GEOMETRIC ENGINE CONSOLE MONITOR ==={RST}")
    for val, label, marker, color in rows:
        print(f"{color}{label}{RST} : {GRAY}[{color}{get_clean_bar(val, marker)}{GRAY}]{RST}")
    print(f"{YLW}========================================{RST}")
    print(f"UP:{YLW}{str(cross_up)}{RST} | DDN:{YLW}{str(cross_dn)}{RST} | Trnd:{trend_color}{trend_str}{RST} ({diff_val:+.2f})")
    print(f"ENTRY: {YLW}{entry}{RST} | EXIT: {YLW}{exit_sig}{RST}")

def log_sync_state(timestamp, entry, exit_sig, price, st):
    """Logs the system state variables cleanly into the target JSON template file."""
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
                except:
                    logs = []
                    
        logs.append(log_entry)
        with open(file_path, "w") as f:
            json.dump(logs[-100:], f, indent=4)
    except:
        pass

def get_signal(df=None):
    """
    Main signal generation function.
    Executes raw state evaluation first, then filters findings into active entries.
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
        o1 = float(last_row['o1'])
        
        cross_up_black = bool(last_row['crossAboveBlack'])
        cross_dn_black = bool(last_row['crossBelowBlack'])
        above_black = bool(last_row['aboveBlack'])
        below_black = bool(last_row['belowBlack'])
        
        # PART 1 MATRIX: Check Candlestick Base Colors
        is_green_c0 = c0 > o0
        is_red_c0   = c0 < o0
        is_green_c1 = c1 > o1
        is_red_c1   = c1 < o1
        
        # --- 4. STEP 1: CALCULATE RAW INDEPENDENT EXIT TREND STATE FIRST ---
        exit_sig = "NONE" # Rule 10 Implementation fallback
        if is_red_c1 and is_green_c0:
            exit_sig = "BUY"  # Rule 6 Execution path
        elif is_green_c1 and is_green_c0:
            exit_sig = "BULL" # Rule 7 Execution path
        elif is_green_c1 and is_red_c0:
            exit_sig = "SELL" # Rule 8 Execution path
        elif is_red_c1 and is_red_c0:
            exit_sig = "BEAR" # Rule 9 Execution path
            
        # --- 5. STEP 2: APPLY FILTERS DIRECTLY ON PRE-COMPUTED EXITS FOR ENTRY ---
        entry = "NONE" # Rule 17 Implementation fallback
        
        # Bullish Entry Rules Cascade Filter
        if cross_up_black:
            entry = "BUY"  # Rule 11 Override
        elif exit_sig == "BUY" and above_black:
            entry = "BUY"  # Rule 12 Confirmation pass
        elif exit_sig == "BULL" and above_black:
            entry = "BULL" # Rule 13 Confirmation pass
            
        # Bearish Entry Rules Cascade Filter
        elif cross_dn_black:
            entry = "SELL" # Rule 14 Override
        elif exit_sig == "SELL" and below_black:
            entry = "SELL" # Rule 15 Confirmation pass
        elif exit_sig == "BEAR" and below_black:
            entry = "BEAR" # Rule 16 Confirmation pass
            
        if DEBUG:
            _print_console_bar(st0, c2, c1, c0, cross_up_black, cross_dn_black, entry, exit_sig)
            
        log_sync_state(df_calc.index[-1], entry, exit_sig, c0, st0)
        return entry, exit_sig
        
    except Exception as e:
        if DEBUG:
            print(f"PXY Master Core Error: {e}")
        return "NONE", "NONE"

# ==================== MAIN EXECUTION INTERFACE INTERSECT ====================
if __name__ == "__main__":
    e, x = get_signal()
    print(f"\nFinal Synchronized Outputs -> Entry Status: {e} | Exit Trend: {x}")


