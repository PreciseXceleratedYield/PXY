# sysmktpxy.py
import numpy as np
import pandas as pd
import json
import os
from datetime import datetime

# Imported from your exact file module name
from sysdthapxy import get_pxy_data

# Global Config
DEBUG = True

def _print_console_bar(c2_c, c1_c, c0_c, c2_o, c1_o, c0_o, entry, exit_sig):
    """ Renders the graphical sorted ASCII price matrix layout inside the console terminal. """
    RST = "\033[0m"
    RED = "\033[91m"
    GRN = "\033[92m"
    YLW = "\033[1;93m"
    GRAY = "\033[90m"

    min_val = min(c2_c, c1_c, c0_c) - 2
    max_val = max(c2_c, c1_c, c0_c) + 2
    scale_width = 20

    def get_clean_bar(val, marker="█"):
        pos = int(((val - min_val) / (max_val - min_val)) * scale_width)
        pos = max(1, pos)
        return (marker * pos).ljust(scale_width)

    c2_color = GRN if c2_c > c2_o else (RED if c2_c < c2_o else YLW)
    c1_color = GRN if c1_c > c1_o else (RED if c1_c < c1_o else YLW)
    c0_color = GRN if c0_c > c0_o else (RED if c0_c < c0_o else YLW)

    rows = [
        (c2_c, f"    C2 -{c2_c:.2f}", "█", c2_color),
        (c1_c, f"    C1 -{c1_c:.2f}", "█", c1_color),
        (c0_c, f"    C0 -{c0_c:.2f}", "█", c0_color)
    ]
    rows.sort(key=lambda item: item[0], reverse=True)

    print(f"\n{YLW}= GEOMETRIC PXY®-PRIORITY ENTRY ENGINE ={RST}")
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
    Asymmetric Dual-Horizon Strategy Engine:
    - Entry Horizon: Confirmed Candlesticks Only (Past 2 vs Past 1) -> Zero Reprinting Risk
    - Exit Horizon : Real-Time Live Running Candlestick (Past 1 vs Live Now) -> Maximum Velocity
    """
    if df is None or len(df) < 5:
        return "NONE", "NONE"

    try:
        # 1. RUN DATAFRAME THROUGH THE ENGINE TRUTH MATRIX
        _, _, _, calculated_df = get_pxy_data(df=df)
        
        if calculated_df is None or calculated_df.empty:
            return "NONE", "NONE"

        # 2. EXTRACT HISTORICAL CANDLE MATRIX ROWS AS SEPARATE HOVER TIME SLICES
        c2_row = calculated_df.iloc[-3]  # Past 2 Candle
        c1_row = calculated_df.iloc[-2]  # Past 1 Candle (Last Completed Close)
        c0_row = calculated_df.iloc[-1]  # Live Running Candle ("Now" Fluctuating)

        # Unpack absolute pricing metrics
        c2_c, c2_o = float(c2_row['Close']), float(c2_row['Open'])
        c1_c, c1_o = float(c1_row['Close']), float(c1_row['Open'])
        c0_c, c0_o = float(c0_row['Close']), float(c0_row['Open'])

        # Establish strict, mutually exclusive direction profiles
        c2_is_green = c2_c > c2_o
        c2_is_red   = c2_c < c2_o

        c1_is_green = c1_c > c1_o
        c1_is_red   = c1_c < c1_o

        c0_is_green = c0_c > c0_o
        c0_is_red   = c0_c < c0_o

        # 3. CALCULATE ASYMMETRIC HORIZONS WITH EXCLUSIVE CONDITIONS

        # --- A. ENTRY SIGNAL: CONFIRMED ENGINE HORIZON (Past 2 vs Past 1) ---
        if c2_is_green and c1_is_green:
            entry = "BULL"
        elif c2_is_red and c1_is_red:
            entry = "BEAR"
        elif c2_is_green and c1_is_red:
            entry = "SELL"
        elif c2_is_red and c1_is_green:
            entry = "BUY"
        else:
            entry = "NONE"

        # --- B. EXIT SIGNAL: LIVE ENGINE HORIZON (Past 1 vs Live Running C0) ---
        if c1_is_green and c0_is_green:
            exit_sig = "BULL"
        elif c1_is_red and c0_is_red:
            exit_sig = "BEAR"
        elif c1_is_green and c0_is_red:
            exit_sig = "SELL"
        elif c1_is_red and c0_is_green:
            exit_sig = "BUY"
        else:
            exit_sig = "NONE"

        # 4. DIAGNOSTICS & STREAM LOGGING
        if DEBUG:
            _print_console_bar(c2_c, c1_c, c0_c, c2_o, c1_o, c0_o, entry, exit_sig)

        # Syncs the JSON file log entry to target the timestamp of the live calculated row
        log_sync_state(calculated_df.index[-1], entry, exit_sig, c0_c)
        
        return entry, exit_sig

    except Exception as e:
        if DEBUG:
            print(f"PXY Matrix Engine Exception: {e}")
        return "NONE", "NONE"

if __name__ == "__main__":
    print("\n[PXY ENGINE STATUS] Asymmetric Confirmed-Entry / Live-Exit Engine Active.")
    print("---------------------------------------------------------------------")
    
    try:
        print("Fetching latest market data from sysdthapxy...")
        _, _, _, live_df = get_pxy_data(df=None)
        
        if live_df is not None and not live_df.empty:
            print(f"Successfully loaded {len(live_df)} rows of live data.")
            
            entry_sig, exit_sig = get_signal(live_df)
            print(f"\n⚡ LIVE ENGINE -> Entry (Confirmed): {entry_sig} | Exit (Live Running): {exit_sig}\n")
        else:
            print("❌ Error: sysdthapxy returned an empty or invalid DataFrame.")
            
    except Exception as e:
        print(f"❌ Failed to execute live stream check: {e}")
