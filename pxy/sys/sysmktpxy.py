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
CHECK_CONFIRMED_ONLY = True  # 🔄 True = Non-Reprinting (Past 2 & Past 1) | False = Live Stream (Past 1 & Live Running)

def _print_console_bar(anchor_c, trigger_c, now_c, anchor_o, trigger_o, now_o, entry, exit_sig):
    """ Renders the graphical sorted ASCII price matrix layout inside the console terminal. """
    RST = "\033[0m"
    RED = "\033[91m"
    GRN = "\033[92m"
    YLW = "\033[1;93m"
    GRAY = "\033[90m"

    min_val = min(anchor_c, trigger_c, now_c) - 2
    max_val = max(anchor_c, trigger_c, now_c) + 2
    scale_width = 20

    def get_clean_bar(val, marker="█"):
        pos = int(((val - min_val) / (max_val - min_val)) * scale_width)
        pos = max(1, pos)
        return (marker * pos).ljust(scale_width)

    anchor_color = GRN if anchor_c >= anchor_o else RED
    trigger_color = GRN if trigger_c >= trigger_o else RED
    now_color = GRN if now_c >= now_o else RED

    rows = [
        (anchor_c, f"    C2 -{anchor_c:.2f}", "█", anchor_color),
        (trigger_c, f"    C1 -{trigger_c:.2f}", "█", trigger_color),
        (now_c, f"  C0 -{now_c:.2f}", "█", now_color)
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
    Dual-Route Strategy Engine mapping either:
    - Confirmed Mode: Past 2 (Anchor) + Past 1 (Trigger) -> Non-Reprinting
    - Live Mode: Past 1 (Anchor) + Live Candle (Trigger) -> Real-Time Speed
    """
    if df is None or len(df) < 5:
        return "NONE", "NONE"

    try:
        # 1. RUN DATAFRAME THROUGH THE ENGINE TRUTH MATRIX
        _, _, _, calculated_df = get_pxy_data(df=df)
        
        if calculated_df is None:
            return "NONE", "NONE"

        # 2. RESOLVE DYNAMIC OFFSETS BASED ON YOUR SWITCH STATE
        if CHECK_CONFIRMED_ONLY:
            # 🔒 Confirmed Non-Reprinting: Past 2 vs Past 1
            anchor_row = calculated_df.iloc[-3]   # Past 2
            trigger_row = calculated_df.iloc[-2]  # Past 1
            log_idx = -2
        else:
            # ⚡ Live Fast Track: Past 1 vs Live Running Candle
            anchor_row = calculated_df.iloc[-2]   # Past 1
            trigger_row = calculated_df.iloc[-1]  # Live Running "Now"
            log_idx = -1

        # Extract values
        anchor_c, anchor_o = float(anchor_row['Close']), float(anchor_row['Open'])
        trigger_c, trigger_o = float(trigger_row['Close']), float(trigger_row['Open'])
        
        # Absolute current live reference for the terminal console UI layout
        now_c, now_o = float(calculated_df.iloc[-1]['Close']), float(calculated_df.iloc[-1]['Open'])

        # 3. CALCULATE DIRECTIONS
        anchor_is_green = anchor_c >= anchor_o
        trigger_is_green = trigger_c >= trigger_o

        # 4. EXECUTE UNIFIED MATRIX PATTERNS
        # Pattern A: Green -> Green
        if anchor_is_green and trigger_is_green:
            entry, exit_sig = "BULL", "BULL"

        # Pattern B: Red -> Red
        elif not anchor_is_green and not trigger_is_green:
            entry, exit_sig = "BEAR", "BEAR"

        # Pattern C: Green -> Red (Down Flip)
        elif anchor_is_green and not trigger_is_green:
            entry, exit_sig = "SELL", "SELL"

        # Pattern D: Red -> Green (Up Flip)
        elif not anchor_is_green and trigger_is_green:
            entry, exit_sig = "BUY", "BUY"

        else:
            entry, exit_sig = "NONE", "NONE"

        # 5. DIAGNOSTICS & STREAM LOGGING
        if DEBUG:
            _print_console_bar(anchor_c, trigger_c, now_c, anchor_o, trigger_o, now_o, entry, exit_sig)

        log_sync_state(calculated_df.index[log_idx], entry, exit_sig, now_c)
        return entry, exit_sig

    except Exception as e:
        if DEBUG:
            print(f"PXY Matrix Engine Exception: {e}")
        return "NONE", "NONE"
if __name__ == "__main__":
    print("\n[PXY ENGINE STATUS] Active Stream Listener Initiated.")
    print(f"Configuration -> CHECK_CONFIRMED_ONLY: {CHECK_CONFIRMED_ONLY}")
    print("--------------------------------------------------")
    
    try:
        print("Fetching latest market data from sysdthapxy...")
        # Call your actual data module with None to let it pull live exchange data
        _, _, _, live_df = get_pxy_data(df=None)
        
        if live_df is not None and not live_df.empty:
            print(f"Successfully loaded {len(live_df)} rows of live data.")
            
            # Execute your engine signal calculations
            entry_sig, exit_sig = get_signal(live_df)
            print(f"\n⚡LIVE ENGINE-> Entry: {entry_sig} | Exit: {exit_sig}\n")
        else:
            print("❌ Error: sysdthapxy returned an empty or invalid DataFrame.")
            
    except Exception as e:
        print(f"❌ Failed to execute live stream check: {e}")
