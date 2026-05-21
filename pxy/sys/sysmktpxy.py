# sysmktpxy.py
import numpy as np
import pandas as pd
import json
import os
from datetime import datetime

# 🔥 FIXED: Imported from your exact file module name
from sysdthapxy import get_ha_data

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

    print(f"\n{YLW}= GEOMETRIC HIGH-PRIORITY ENTRY ENGINE ={RST}")
    for val, label, marker, color in rows:
        print(f"{color}{label}{RST} : {GRAY}[{color}{get_clean_bar(val, marker)}{GRAY}]{RST}")
    print(f"{YLW}========================================{RST}")
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
    3-Bar Vector Engine wrapped around imported functional core data streams.
    """
    if df is None or len(df) < 5:
        return "NONE", "NONE"

    try:
        # 1. RUN DATAFRAME THROUGH THE ENGINE TRUTH MATRIX
        _, _, _, calculated_df = get_ha_data(df=df)
        
        if calculated_df is None or "ha_signal" not in calculated_df.columns:
            return "NONE", "NONE"

        # 2. EXTRACT TRUTH DATA FROM LAST INDEX
        last_idx = calculated_df.index[-1]
        raw_signal = str(calculated_df.at[last_idx, "ha_signal"]).upper()
        
        # 3. COORDINATE MAPPING FOR VISUALIZER BAR (STAYS STANDARD PRICE)
        c0, o0 = float(calculated_df.at[last_idx, 'Close']), float(calculated_df.at[last_idx, 'Open'])
        c1, o1 = float(calculated_df.iloc[-2]['Close']), float(calculated_df.iloc[-2]['Open'])
        c2, o2 = float(calculated_df.iloc[-3]['Close']), float(calculated_df.iloc[-3]['Open'])

        # 4. RESOLVE SIGNALS
        if raw_signal in ["BUY", "SELL", "BULL", "BEAR"]:
            entry = raw_signal
            exit_sig = raw_signal
        else:
            # Fallback tracking if engine registers a "none" string value
            entry = "BULL" if c0 >= c1 else "BEAR"
            exit_sig = entry

        # 5. DIAGNOSTICS & STREAM LOGGING
        if DEBUG:
            _print_console_bar(c2, c1, c0, o2, o1, o0, entry, exit_sig)

        log_sync_state(calculated_df.index[-1], entry, exit_sig, c0)
        return entry, exit_sig

    except Exception as e:
        if DEBUG:
            print(f"PXY High-Priority Vector Engine Exception: {e}")
        return "NONE", "NONE"


