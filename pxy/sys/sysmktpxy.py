# sysmktpxy.py
import numpy as np
import pandas as pd
import json
import os
from datetime import datetime
from sysdtafpxy import fetch_yf_data
from sysstrndpxy import calculate_supertrend

# Uses your upgraded TSMA(42) + Price Midpoint architecture
DEBUG = True

def _print_console_bar(st, c2, c1, c0, cross_up, cross_dn):
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

    # Build row items for descending sort logic
    # Structure: (numerical_value, formatted_label_prefix, bar_marker, label_color)
    rows = [
        (st, f"ST-{st:.2f}", "-", RED),
        (c2, f"C2-{c2:.2f}", "█", GRN),
        (c1, f"C1-{c1:.2f}", "█", GRN),
        (c0, f"C0-{c0:.2f}", "█", GRN)
    ]
    
    # Strictly sort rows by the numerical value in descending order (highest price on top)
    rows.sort(key=lambda item: item[0], reverse=True)

    print(f"\n{YLW}=== GEOMETRIC ENGINE CONSOLE MONITOR ==={RST}")
    for val, label, marker, color in rows:
        print(f"{color}{label}{RST} : {GRAY}[{color}{get_clean_bar(val, marker)}{GRAY}]{RST}")
    print(f"{YLW}========================================{RST}")
    print(f"UP:{YLW}{str(cross_up)}{RST} | DDN:{YLW}{str(cross_dn)}{RST} | Trnd:{trend_color}{trend_str}{RST} ({diff_val:+.2f})")

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
    Evaluates V-patterns, 3-candle lines, and black line crossovers to output entry status and exit trend.
    """
    if df is None:
        df = fetch_yf_data()
    if df is None or df.empty:
        return "NONE", "NONE"
        
    try:
        # --- 1. RUN STRUCTURAL SUPERTREND BACKBONE ---
        df_calc = calculate_supertrend(df)
        
        # --- 2. SIGNAL MATRIX LOOKBACK SHIFTS (STRICT C0, C1, C2 AND ST ONLY) ---
        df_calc['c1'] = df_calc['Close'].shift(1)
        df_calc['c2'] = df_calc['Close'].shift(2)
        df_calc['st1'] = df_calc['ST'].shift(1)
        
        df_calc['aboveBlack'] = df_calc['Close'] > df_calc['ST']
        df_calc['belowBlack'] = df_calc['Close'] < df_calc['ST']
        
        df_calc['crossAboveBlack'] = (df_calc['c1'] <= df_calc['st1']) & (df_calc['Close'] > df_calc['ST'])
        df_calc['crossBelowBlack'] = (df_calc['c1'] >= df_calc['st1']) & (df_calc['Close'] < df_calc['ST'])
        
        # --- 3. ISOLATE VECTOR STATES FROM LAST ROW ---
        last_row = df_calc.iloc[-1].copy()
        c0, st0 = float(last_row['Close']), float(last_row['ST'])
        c1, c2 = float(last_row['c1']), float(last_row['c2'])
        
        cross_up_black = bool(last_row['crossAboveBlack'])
        cross_dn_black = bool(last_row['crossBelowBlack'])
        
        v_pattern_up = (c1 < c2) and (c0 > c1)
        inverted_v_down = (c1 > c2) and (c0 < c1)
        three_candles_up = (c0 > c1) and (c1 > c2)
        three_candles_down = (c0 < c1) and (c1 < c2)
        
        st_signal = str(last_row['ST_Trend'])
        above_black = bool(last_row['aboveBlack'])
        below_black = bool(last_row['belowBlack'])
        
        if DEBUG:
            _print_console_bar(st0, c2, c1, c0, cross_up_black, cross_dn_black)
            
        # --- 4. ENTRY SIGNAL EXECUTION ENGINE ---
        entry = "NONE"
        if st_signal == "BUY" or cross_up_black:
            entry = "BUY"
        elif st_signal == "SELL" or cross_dn_black:
            entry = "SELL"
        elif v_pattern_up and above_black:
            entry = "BUY"
        elif inverted_v_down and below_black:
            entry = "SELL"
        elif three_candles_up and above_black:
            entry = "BULL"
        elif three_candles_down and below_black:
            entry = "BEAR"
            
        # --- 5. EXIT SIGNAL ENGINE ---
        exit_sig = "SIDE"
        if st_signal == "BUY" or cross_up_black:
            exit_sig = "BUY"
        elif st_signal == "SELL" or cross_dn_black:
            exit_sig = "SELL"
        elif v_pattern_up:
            exit_sig = "BUY"
        elif inverted_v_down:
            exit_sig = "SELL"
        elif three_candles_up:
            exit_sig = "BULL"
        elif three_candles_down:
            exit_sig = "BEAR"
        else:
            exit_sig = "NONE"
            
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

