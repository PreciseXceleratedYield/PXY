# sysmktpxy.py
import numpy as np
import pandas as pd
import json
import os
from datetime import datetime

# 🔥 SURGICAL UPDATE: Import both the confirmed and live variants from your core engine
from sysdthapxy import get_pxy_data, get_pxy_live_data

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
        (c2, f"    ② C2-{c2:.2f}", "█", c2_color),
        (c1, f"    ① C1-{c1:.2f}", "█", c1_color),
        (c0, f"    ⓪ C0-{c0:.2f}", "█", c0_color)
    ]
    rows.sort(key=lambda item: item[0], reverse=True)

    print(f"\n{YLW}= GEOMETRIC HIGH-PRIORITY ENTRY ENGINE ={RST}")
    for val, label, marker, color in rows:
        print(f"{color}{label}{RST} : {GRAY}[{color}{get_clean_bar(val, marker)}{GRAY}]{RST}")
    print(f"{YLW}========================================{RST}")

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
        # ==============================================================================
        # SURGICAL UPDATE: INDEPENDENT DATA PROCESSING LINES
        # ==============================================================================
        # 1A. Fetch CONFIRMED Dataframe strictly for Entries
        _, _, _, confirmed_df = get_pxy_data(df=df)
        
        # 1B. Fetch LIVE RUNNING Dataframe strictly for Exits
        _, _, _, live_df = get_pxy_live_data(df=df)
        
        # Column validation on both generated frames
        if confirmed_df is None or "pxy_signal" not in confirmed_df.columns:
            return "NONE", "NONE"
        if live_df is None or "pxy_signal" not in live_df.columns:
            return "NONE", "NONE"

        # 2. EXTRACT TRACKING DATA TARGETS
        idx_confirmed = confirmed_df.index[-1]
        idx_live      = live_df.index[-1]
        
        # Entry reads from confirmed (closed) frame, Exit reads from live (ticking) frame
        raw_entry_signal = str(confirmed_df.at[idx_confirmed, "pxy_signal"]).upper()
        raw_exit_signal  = str(live_df.at[idx_live, "pxy_signal"]).upper()
        
        # 3. COORDINATE MAPPING FOR VISUALIZER BAR (Pulls from Confirmed Frame for standard stability)
        c0, o0 = float(confirmed_df.at[idx_confirmed, 'Close']), float(confirmed_df.at[idx_confirmed, 'Open'])
        c1, o1 = float(confirmed_df.iloc[-2]['Close']), float(confirmed_df.iloc[-2]['Open'])
        c2, o2 = float(confirmed_df.iloc[-3]['Close']), float(confirmed_df.iloc[-3]['Open'])

        # 4. RESOLVE FINAL ASYMMETRICAL DATA STATE 
        entry    = raw_entry_signal if raw_entry_signal in ["BUY", "SELL", "BULL", "BEAR"] else ("BULL" if c0 >= c1 else "BEAR")
        exit_sig = raw_exit_signal if raw_exit_signal in ["BUY", "SELL", "BULL", "BEAR"] else entry

        # 5. DIAGNOSTICS & STREAM LOGGING
        if DEBUG:
            _print_console_bar(c2, c1, c0, o2, o1, o0, entry, exit_sig)

        log_sync_state(confirmed_df.index[-1], entry, exit_sig, c0)
        return entry, exit_sig

    except Exception as e:
        if DEBUG:
            print(f"PXY High-Priority Vector Engine Exception: {e}")
        return "NONE", "NONE"
