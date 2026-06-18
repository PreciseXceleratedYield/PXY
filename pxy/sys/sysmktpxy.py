# sysmktpxy.py
import numpy as np
import pandas as pd
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
        (c0_c, f" 0 (Live) -{c0_c % 100:05.1f}", c0_ansi),
        (c1_c, f" 1 (Conf) -{c1_c % 100:05.1f}", c1_ansi),
        (c2_c, f" 2 (Past) -{c2_c % 100:05.1f}", c2_ansi)
    ]

    print(f"\n{YLW}= GEOMETRIC PXY®-PRIORITY ENGINE ={RST}")
    for val, label, color in rows:
        print(f"{color}{label}{RST} : {GRAY}[{color}{get_clean_bar(val)}{GRAY}]{RST}")
    print(f"{YLW}========================================{RST}")

def get_signal(df):
    """ 
    Symmetric Live Ingestion Engine:
    - Directly extracts raw signal from upstream and passes it to entry/exit horizons.
    """
    if df is None or len(df) < 5:
        return "NONE", "NONE"

    try:
        # 1. READ DATAFRAME MATRIX FROM THE UPSTREAM ENGINE TRUTH GATEWAY
        _, _, _, calculated_df = get_pxy_data(df=df)
        
        if calculated_df is None or calculated_df.empty:
            return "NONE", "NONE"

        # 2. EXTRACT PRE-COMPUTED STRAT MATRIX VALUES VIA UPSTREAM HOVER TIME SLICES
        c2_color = str(calculated_df.iloc[-3]['pxy_color']).lower().strip()
        c1_color = str(calculated_df.iloc[-2]['pxy_color']).lower().strip()
        c0_color = str(calculated_df.iloc[-1]['pxy_color']).lower().strip()

        # Extract absolute price metrics for the visualizer
        c2_c = float(calculated_df.iloc[-3]['Close'])
        c1_c = float(calculated_df.iloc[-2]['Close'])
        c0_c = float(calculated_df.iloc[-1]['Close'])

        # 3. DIRECT RAW SIGNAL PASS-THROUGH
        upstream_signal = str(calculated_df.iloc[-1]['pxy_signal']).upper().strip()
        
        entry = upstream_signal
        exit_sig = upstream_signal

        # 4. DIAGNOSTICS
        if DEBUG:
            _print_console_bar(c2_c, c1_c, c0_c, c2_color, c1_color, c0_color, entry, exit_sig)
        
        return entry, exit_sig

    except Exception as e:
        if DEBUG:
            print(f"PXY Matrix Engine Exception: {e}")
        return "NONE", "NONE"

if __name__ == "__main__":
    print("\n[PXY ENGINE STATUS] Pure Upstream Cascade Signal Ingestion Active.")
    print("---------------------------------------------------------------------")
    
    try:
        print("Fetching latest pre-computed market data matrix from upstream framework...")
        _, _, _, live_df = get_pxy_data(df=None)
        
        if live_df is not None and not live_df.empty:
            print(f"Successfully loaded {len(live_df)} rows of live streaming data.")
            
            entry_sig, exit_sig = get_signal(live_df)
            print(f"\n⚡ LIVE ENGINE -> Entry (As-Is): {entry_sig} | Exit (As-Is): {exit_sig}\n")
        else:
            print("❌ Error: Upstream architecture returned an empty or invalid DataFrame.")
            
    except Exception as e:
        print(f"❌ Failed to execute live stream check: {e}")



