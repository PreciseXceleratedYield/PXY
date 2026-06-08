# sysmktpxy.py
import numpy as np
import pandas as pd
import json
import os
from datetime import datetime

# Imported from your upstream data engine module
from sysdthapxy import get_pxy_data

# Global Config
DEBUG = True

def _print_console_bar(c2_c, c1_c, c0_c, c2_color, c1_color, c0_color, entry, exit_sig):
    """ Renders the graphical sorted ASCII price matrix layout inside the console terminal. """
    RST = "\033[0m"
    RED = "\033[91m"
    GRN = "\033[92m"
    YLW = "\033[1;93m"
    GRAY = "\033[90m"

    def get_color_ansi(color_str):
        if color_str == "green": return GRN
        if color_str == "red": return RED
        return YLW

    min_val = min(c2_c, c1_c, c0_c) - 2
    max_val = max(c2_c, c1_c, c0_c) + 2
    scale_width = 20

    def get_clean_bar(val):
        pos = int(((val - min_val) / (max_val - min_val)) * scale_width)
        pos = max(1, pos)
        return ("█" * pos).ljust(scale_width)

    c2_ansi = get_color_ansi(c2_color)
    c1_ansi = get_color_ansi(c1_color)
    c0_ansi = get_color_ansi(c0_color)

    rows = [
        (c2_c, f"    C2 -{c2_c:.2f}", c2_ansi),
        (c1_c, f"    C1 -{c1_c:.2f}", c1_ansi),
        (c0_c, f"    C0 -{c0_c:.2f}", c0_ansi)
    ]
    rows.sort(key=lambda item: item[0], reverse=True)

    print(f"\n{YLW}= GEOMETRIC PXY®-PRIORITY ENGINE STATE ={RST}")
    for val, label, color in rows:
        print(f"{color}{label}{RST} : {GRAY}[{color}{get_clean_bar(val)}{GRAY}]{RST}")
    print(f"{GRAY}----------------------------------------{RST}")
    print(f"  🔒 ENTRY (Confirm): {entry}")
    print(f"  📡 EXIT (Upstream): {exit_sig}")
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
    - Exit Horizon : Straight Ingestion from Upstream Strategy Pipeline Matrix -> Raw Signal Pass
    """
    if df is None or len(df) < 5:
        return "NONE", "NONE"

    try:
        # 1. READ DATAFRAME MATRIX FROM THE UPSTREAM ENGINE TRUTH GATEWAY
        _, _, _, calculated_df = get_pxy_data(df=df)
        
        if calculated_df is None or calculated_df.empty:
            return "NONE", "NONE"

        # 2. EXTRACT PRE-COMPUTED STRAT MATRIX VALUES VIA UPSTREAM HOVER TIME SLICES
        c2_color = str(calculated_df.iloc[-3]['pxy_color']).lower().strip()  # Past 2 Candle Color
        c1_color = str(calculated_df.iloc[-2]['pxy_color']).lower().strip()  # Past 1 Candle Color (Last Closed)
        c0_color = str(calculated_df.iloc[-1]['pxy_color']).lower().strip()  # Live Running Candle Color ("Now")

        # Extract absolute price metrics to feed back into the graphical ASCII printer
        c2_c = float(calculated_df.iloc[-3]['Close'])
        c1_c = float(calculated_df.iloc[-2]['Close'])
        c0_c = float(calculated_df.iloc[-1]['Close'])

        # DIRECT UPSTREAM INGESTION FOR THE EXIT SIGNAL
        exit_sig = str(calculated_df.iloc[-1]['pxy_signal']).upper().strip()

        # Establish strict binary direction flags purely from upstream tracking definitions
        c2_is_green = c2_color == "green"
        c2_is_red   = c2_color == "red"

        c1_is_green = c1_color == "green"
        c1_is_red   = c1_color == "red"

        # 3. EXCLUSIVE PATTERN GENERATION FOR CONFIRMED ENTRY

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

        # 4. DIAGNOSTICS & STREAM LOGGING
        if DEBUG:
            _print_console_bar(c2_c, c1_c, c0_c, c2_color, c1_color, c0_color, entry, exit_sig)

        # Syncs the JSON file log entry to target the timestamp of the live calculated row
        log_sync_state(calculated_df.index[-1], entry, exit_sig, c0_c)
        
        return entry, exit_sig

    except Exception as e:
        if DEBUG:
            print(f"PXY Matrix Engine Exception: {e}")
        return "NONE", "NONE"

if __name__ == "__main__":
    print("\n[PXY ENGINE STATUS] Confirmed-Entry / Upstream-Exit Ingestion Engine Active.")
    print("---------------------------------------------------------------------")
    
    try:
        print("Fetching latest pre-computed market data matrix from upstream framework...")
        _, _, _, live_df = get_pxy_data(df=None)
        
        if live_df is not None and not live_df.empty:
            print(f"Successfully loaded {len(live_df)} rows of live streaming data.")
            
            entry_sig, exit_sig = get_signal(live_df)
            print(f"\n⚡ LIVE ENGINE -> Entry (Confirmed): {entry_sig} | Exit (Upstream Raw): {exit_sig}\n")
        else:
            print("❌ Error: Upstream architecture returned an empty or invalid DataFrame.")
            
    except Exception as e:
        print(f"❌ Failed to execute live stream check: {e}")


