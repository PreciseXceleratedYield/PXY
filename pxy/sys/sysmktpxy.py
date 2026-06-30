import os
import sys
import json
import numpy as np
import pandas as pd
from datetime import datetime
from sysdtafpxy import fetch_yf_data

# Global Configuration
DEBUG = True

def export_supertrend_json(df: pd.DataFrame, output_file=None) -> list:
    """Dumps tracking metrics using backward-compatible structure for live downstream charts."""
    if df is None or df.empty:
        return []
    
    if output_file is None:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        output_file = os.path.abspath(os.path.join(base_dir, "web", "webchrtpxy.json"))
        
    output = []
    for idx, row in df.iterrows():
        output.append({
            "time": str(idx),
            "close": float(row["Close"]),
            "p_master": float(row["Close"]),
            "st": float(row["Close"]),         
            "st_trend": str(row["sma_trend"]), 
            "sma_line": float(row["Close"]),   
            "sma_trend": str(row["sma_trend"])
        })
        
    out_dir = os.path.dirname(output_file)
    if out_dir and not os.path.exists(out_dir):
        os.makedirs(out_dir, exist_ok=True)
        
    with open(output_file, "w") as f:
        json.dump(output, f, indent=2)
        
    return output

def calculate_supertrend(df: pd.DataFrame) -> pd.DataFrame:
    """
    PXY® Geometric Data Matrix Framework
    Calculates UP/DOWN states up to the active live tick for chart synchronization.
    """
    df = df.copy()
    n = len(df)
    
    trends = ["NONE"] * n
    close_vals = df['Close'].to_numpy()
    
    # Process historical trends based on sequential close logic
    for i in range(1, n):
        if close_vals[i] > close_vals[i - 1]:
            trends[i] = "UP"
        elif close_vals[i] < close_vals[i - 1]:
            trends[i] = "DOWN"
        else:
            trends[i] = "NONE"
            
    df['sma_trend'] = trends
    
    # Slice matrix to exactly 50 rows for JSON dashboard compliance
    df = df.tail(50).copy()
    df['bar_count'] = np.arange(1, len(df) + 1)
    
    return df

def _print_console_bar(c1, c0, execution_state):
    """Renders the graphical console display profiling the active live running candle."""
    RST = "\033[0m"
    RED = "\033[91m"
    GRN = "\033[92m"
    YLW = "\033[1;93m"
    GRAY = "\033[90m"

    min_val = min(int(c1), int(c0)) - 2
    max_val = max(int(c1), int(c0)) + 2
    scale_width = 20

    def get_clean_bar(val, marker="█"):
        pos = int(((val - min_val) / (max_val - min_val)) * scale_width) if max_val != min_val else 1
        pos = max(1, pos)
        return (marker * pos).ljust(scale_width)

    # Color assignment bound to directional results
    state_color = GRN if execution_state == "UP" else (RED if execution_state == "DOWN" else YLW)

    # Integer transformations applied directly within the structural statements
    rows = [
        (int(c1), f"CLOSED C1-{int(c1)}", "█", GRAY),
        (int(c0), f"ACTIVE C0-{int(c0)}", "█", state_color)  # Live tick visual anchor
    ]
    rows.sort(key=lambda item: item[0], reverse=True)

    print(f"\n{YLW}==GEOMETRIC ENGINE CONSOLE MONITOR(LIVE)=={RST}")
    for val, label, marker, color in rows:
        print(f"{color}{label}{RST} : {GRAY}[{color}{get_clean_bar(val, marker)}{GRAY}]{RST}")
    print(f"{YLW}=========================================={RST}")
    print(f"       ACTIVE RUNNING CANDLE STATE: {state_color}{execution_state}{RST}")

def log_sync_state(timestamp, signal_state, price):
    """Logs the active system state variables directly using live active parameters."""
    try:
        dir_path = os.path.expanduser("~/pxy")
        os.makedirs(dir_path, exist_ok=True)
        file_path = os.path.join(dir_path, "tv_sync_log.json")

        log_entry = {
            "Timestamp": str(timestamp),
            "Price": float(price),
            "Signal_State": str(signal_state),
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
    Main pipeline stream evaluating ONLY the active live running candle (Index -1).
    Completely bypasses confirmed historical lockouts to prevent execution latency.
    """
    if df is None:
        df = fetch_yf_data()
        
    if df is None or len(df) < 2:
        return "NONE", "NONE"

    try:
        # --- 1. EXTRACT DATA FOR PREVIOUS CLOSED CANDLE (INDEX -2) ---
        closed_row = df.iloc[-2]
        c1 = float(closed_row['Close'])

        # --- 2. EXTRACT DATA FOR LIVE ACTIVE RUNNING CANDLE (INDEX -1) ---
        live_row = df.iloc[-1]
        c0 = float(live_row['Close'])

        # --- 3. EXECUTE EXCLUSIVE LIVE RUNNING LOGIC MATCHING ---
        if c0 > c1:
            execution_state = "UP"
        elif c0 < c1:
            execution_state = "DOWN"
        else:
            execution_state = "NONE"

        # --- 4. TELEMETRY MONITORING & STORAGE ---
        if DEBUG:
            _print_console_bar(c1, c0, execution_state)
            
        # Log and tag system state using active running index timestamp (-1)
        log_sync_state(df.index[-1], execution_state, c0)
        
        # Dual-return alignment matching entry and exit variables identically
        return execution_state, execution_state

    except Exception as e:
        if DEBUG:
            print(f"Signal Processing Engine Exception: {e}")
        return "NONE", "NONE"

if __name__ == "__main__":
    print("=== STARTING PXY LIVE RUNNING CANDLE GEOMETRIC ENGINE ===")
    raw_df = fetch_yf_data()
    
    if raw_df is not None and not raw_df.empty:
        # Process and sync dynamic data frame matrices
        processed_df = calculate_supertrend(raw_df)
        print(f"[SUCCESS] Calculated Matrix. Sliced Rows for Export: {len(processed_df)}")
        
        # Sync and update chart dashboard JSON files
        export_supertrend_json(processed_df)
        
        signal, _ = get_signal(raw_df)
        print(f"\nCalculated Dynamic Live State: {signal}")
    else:
        print("[WARNING] Upstream connection returned an empty historical dataset matrix.")

