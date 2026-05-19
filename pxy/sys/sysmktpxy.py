# sysmktpxy.py
import numpy as np
import pandas as pd
import json
import os
from datetime import datetime

# Global Config
DEBUG = True

def _print_console_bar(c2, c1, c0, o2, o1, o0, entry, exit_sig):
    """ Renders the graphical sorted ASCII price matrix layout inside the console terminal. """
    RST = "\033[0m"
    RED = "\033[91m"
    GRN = "\033[92m"
    YLW = "\033[1;93m"
    GRAY = "\033[90m"

    min_val = min(c2, c1, c0) - 2
    max_val = max(c2, c1, c0) + 2
    scale_width = 20

    def get_clean_bar(val, marker="█"):
        pos = int(((val - min_val) / (max_val - min_val)) * scale_width)
        pos = max(1, pos)
        return (marker * pos).ljust(scale_width)

    c2_color = GRN if c2 >= o2 else RED
    c1_color = GRN if c1 >= o1 else RED
    c0_color = GRN if c0 >= o0 else RED

    rows = [
        (c2, f"C2-{c2:.2f}", "█", c2_color),
        (c1, f"C1-{c1:.2f}", "█", c1_color),
        (c0, f"C0-{c0:.2f}", "█", c0_color)
    ]
    rows.sort(key=lambda item: item, reverse=True)

    print(f"\n{YLW}=== GEOMETRIC V-ENGINE MONITOR ==={RST}")
    for val, label, marker, color in rows:
        print(f"{color}{label}{RST} : {GRAY}[{color}{get_clean_bar(val, marker)}{GRAY}]{RST}")
    print(f"{YLW}==================================={RST}")
    print(f" ENTRY SIGNAL: {YLW}{entry}{RST} | EXIT SIGNAL: {YLW}{exit_sig}{RST}")

def log_sync_state(timestamp, entry, exit_sig, price):
    """ Logs the synchronized system state variables into a local rolling JSON buffer. """
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

def get_signal(df):
    """ 
    3-Bar Vector Engine evaluating V-Flips, Inverted V-Flips, and Continuations.
    """
    if df is None or len(df) < 3:
        return "NONE", "NONE"

    try:
        df = df.copy()
        
        # --------------------------------------------------
        # CRASH PROTECTION: DYNAMIC UPSTREAM COLUMN MAPPING
        # --------------------------------------------------
        if 'is_green' not in df.columns:
            green_col = [c for c in df.columns if 'green' in str(c).lower()]
            df['is_green'] = df[green_col[0]] if green_col else df['Close'] > df['Open']

        if 'is_red' not in df.columns:
            red_col = [c for c in df.columns if 'red' in str(c).lower()]
            df['is_red'] = df[red_col[0]] if red_col else df['Close'] < df['Open']

        # FIXED: Added the proper '.str' accessor before calling '.strip()' on Pandas series objects
        df['is_green'] = df['is_green'].astype(str).str.lower().str.strip().isin(['true', '1', '1.0', '2', '2.0', 'green', 'yes'])
        df['is_red']   = df['is_red'].astype(str).str.lower().str.strip().isin(['true', '1', '1.0', 'red', 'yes'])

        # --------------------------------------------------
        # EXTRACT CANDLES: LIVE (0), PREVIOUS (1), PREV-2 (2)
        # --------------------------------------------------
        last_idx = df.index[-1]
        
        # Candle 0 (Current Live Bar)
        is_live_green = bool(df.at[last_idx, 'is_green'])
        is_live_red   = bool(df.at[last_idx, 'is_red'])
        
        # Candle -1 (Previous Bar)
        is_prev1_green = bool(df['is_green'].iloc[-2])
        is_prev1_red   = bool(df['is_red'].iloc[-2])
        
        # Candle -2 (Two Bars Ago)
        is_prev2_green = bool(df['is_green'].iloc[-3])
        is_prev2_red   = bool(df['is_red'].iloc[-3])
        
        # Console visual layout variables
        c0, o0 = float(df.at[last_idx, 'Close']), float(df.at[last_idx, 'Open'])
        c1, o1 = float(df.iloc[-2]['Close']), float(df.iloc[-2]['Open'])
        c2, o2 = float(df.iloc[-3]['Close']), float(df.iloc[-3]['Open'])

        # --------------------------------------------------
        # EXCLUSIVE MATRIX FILTER GATES
        # --------------------------------------------------
        # V-Pattern: Green -> Red -> Green
        v_buy = is_prev2_green and is_prev1_red and is_live_green
        
        # Inverted V-Pattern: Red -> Green -> Red
        inverted_v_sell = is_prev2_red and is_prev1_green and is_live_red
        
        # Continuation Trends (All 3 match in a row)
        continuation_bull = is_prev2_green and is_prev1_green and is_live_green
        continuation_bear = is_prev2_red and is_prev1_red and is_live_red

        # --------------------------------------------------
        # SIGNAL ROUTING LOGIC
        # --------------------------------------------------
        if v_buy:
            entry, exit_sig = "BUY", "BUY"
        elif inverted_v_sell:
            entry, exit_sig = "SELL", "SELL"
        elif continuation_bull:
            entry, exit_sig = "BULL", "BULL"
        elif continuation_bear:
            entry, exit_sig = "BEAR", "BEAR"
        else:
            entry, exit_sig = "NONE", "NONE"

        if DEBUG:
            _print_console_bar(c2, c1, c0, o2, o1, o0, entry, exit_sig)

        log_sync_state(df.index[-1], entry, exit_sig, c0)
        return entry, exit_sig

    except Exception as e:
        if DEBUG:
            print(f"PXY Vector Engine Exception: {e}")
        return "NONE", "NONE"

if __name__ == "__main__":
    dates = pd.date_range(start="2026-01-01", periods=3, freq="min")
    test_df = pd.DataFrame({
        'Open': [100, 101, 102],
        'Close': [101, 102, 103],
        'is_green': ['2', '2', '2'],
        'is_red': [False, False, False]
    }, index=dates)
    
    e, x = get_signal(test_df)
    print(f"\n=== Verification Output -> Entry: {e} | Exit: {x} ===")

