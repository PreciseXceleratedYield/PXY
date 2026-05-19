# sysmktpxy.py
import numpy as np
import pandas as pd
import json
import os
from datetime import datetime
from sysdtafpxy import fetch_yf_data
from sysstrndpxy import calculate_supertrend # <-- Import from Tier 1 Core
from sysstrhpxy import get_candle_strength_line # <-- Import your streak module

# Global Config
DEBUG = True

def _print_console_bar(st, c2, c1, c0, o2, o1, o0, cross_up, cross_dn, entry, exit_sig):
    """ Renders the graphical sorted ASCII price matrix layout inside the console terminal. """
    RST = "\033[0m"
    RED = "\033[91m"
    GRN = "\033[92m"
    YLW = "\033[1;93m"
    GRAY = "\033[90m"

    min_val = min(c2, c1, c0, st) - 2
    max_val = max(c2, c1, c0, st) + 2
    scale_width = 20

    def get_clean_bar(val, marker="█"):
        pos = int(((val - min_val) / (max_val - min_val)) * scale_width)
        pos = max(1, pos)
        return (marker * pos).ljust(scale_width)

    trend_str = "BULL" if c0 >= st else "BEAR"
    trend_color = GRN if c0 >= st else RED

    c2_color = GRN if c2 >= o2 else RED
    c1_color = GRN if c1 >= o1 else RED
    c0_color = GRN if c0 >= o0 else RED

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
    print(f"UP:{YLW}{str(cross_up)}{RST} | DDN:{YLW}{str(cross_dn)}{RST} | Trnd:{trend_color}{trend_str}{RST}")
    print(f" ENTRY: {YLW}{entry}{RST} | EXIT: {YLW}{exit_sig}{RST}")

def log_sync_state(timestamp, entry, exit_sig, price, st):
    """ Logs the synchronized system state variables into a local rolling JSON buffer. """
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
    """ Processes positional vectors, extracts upstream states, and tracks metrics. """
    if df is None:
        df = fetch_yf_data()
    if df is None or df.empty:
        return "NONE", "NONE"

    try:
        df_calc = calculate_supertrend(df)
        df_calc['c1'] = df_calc['Close'].shift(1)
        df_calc['c2'] = df_calc['Close'].shift(2)
        df_calc['o1'] = df_calc['Open'].shift(1)
        df_calc['o2'] = df_calc['Open'].shift(2)
        df_calc['st1'] = df_calc['ST'].shift(1)

        # Crossover Tracking Logic
        df_calc['crossAboveBlack'] = (df_calc['c1'] <= df_calc['st1']) & (df_calc['Close'] > df_calc['ST'])
        df_calc['crossBelowBlack'] = (df_calc['c1'] >= df_calc['st1']) & (df_calc['Close'] < df_calc['ST'])

        last_row = df_calc.iloc[-1].copy()
        c0, st0 = float(last_row['Close']), float(last_row['ST'])
        o0 = float(last_row['Open'])
        c1, c2 = float(last_row['c1']), float(last_row['c2'])
        o1, o2 = float(last_row['o1']), float(last_row['o2'])
        cross_up_black = bool(last_row['crossAboveBlack'])
        cross_dn_black = bool(last_row['crossBelowBlack'])

        # --------------------------------------------------
        # STREAK LOGIC & SUPERTREND OVERRIDE INTEGRATION
        # --------------------------------------------------
        # Fetch the standalone streak signal from your system module
        raw_streak = get_candle_strength_line(df=df_calc)
        
        # Clean string to safely process alternative formats
        streak_signal = str(raw_streak).replace("⚡", "").strip().upper()

        # PRIORITY 1: Only catch explicit trading actions from Streak Module
        if streak_signal == "BUY":
            entry = "BUY"
            exit_sig = "BUY"
        elif streak_signal == "SELL":
            entry = "SELL"
            exit_sig = "SELL"
        
        # PRIORITY 2: Drop into Fallback only on explicit SuperTrend crossovers
        else:
            if cross_up_black:
                entry = "BUY"
                exit_sig = "BUY"
            elif cross_dn_black:
                entry = "SELL"
                exit_sig = "SELL"
            else:
                # If no streak flip occurs and no SuperTrend line breakout occurs, stay neutral
                entry = "NEUTRAL"
                exit_sig = "NEUTRAL"

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
    print(f"\n=== [TIER 2] Synchronized Outputs -> Entry: {e} | Exit: {x} ===")



