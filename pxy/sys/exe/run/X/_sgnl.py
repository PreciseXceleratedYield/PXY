# _sgnl.py
import os
import sys
import warnings
import json
from pathlib import Path
from datetime import datetime
import pytz
import numpy as np
import pandas as pd
import yfinance as yf

SYS_DIR = Path(__file__).resolve().parents[3]
if str(SYS_DIR) not in sys.path:
    sys.path.insert(0, str(SYS_DIR))
from sysmodepxy import dispatch_mode

# Silence formatting warnings completely
warnings.simplefilter(action='ignore', category=FutureWarning)

# =====================================================================
# STRATEGY CORE CONSTANTS
# =====================================================================
TICKER = "^NSEI"               # Tracking NIFTY 50 Index
TIMEZONE = "Asia/Kolkata"       # Local execution context (IST)
JSON_OUTPUT = "_sgnl.json"      # Keeping file in the same folder

def _pad_line_to_42(visible_text, ansi_prefix="", ansi_suffix=""):
    """
    Ensures the printed line takes up exactly 42 character spaces.
    Emojis are counted as 2 characters. Invisible ANSI codes are excluded.
    """
    visual_len = 0
    for char in visible_text:
        if ord(char) > 0x2000:  
            visual_len += 2
        else:
            visual_len += 1
            
    padding_needed = 42 - visual_len
    
    if padding_needed > 0:
        return f"{ansi_prefix}{visible_text}{' ' * padding_needed}{ansi_suffix}"
    else:
        return f"{ansi_prefix}{visible_text[:42]}{ansi_suffix}"

def _print_console_bar(c2, c1, c0, o2, o1, o0, entry, exit_sig):
    """ Renders the graphical sorted ASCII price matrix layout inside the console terminal at exactly 42 width. """
    RST = "\033[0m"
    RED = "\033[91m"
    GRN = "\033[92m"
    YLW = "\033[1;93m"

    header_emoji = " 🐂" if entry in ["BUY", "BULL"] else " 🐻"
    header_text = f"{header_emoji} GEOMETRIC MATRIX ENGINE"
    border_text = "==========================================" 

    min_val = min(c2, c1, c0) - 2
    max_val = max(c2, c1, c0) + 2
    scale_width = 23

    def get_clean_bar(val, marker="█"):
        pos = int(((val - min_val) / (max_val - min_val)) * scale_width)
        pos = max(1, min(pos, scale_width))
        return (marker * pos).ljust(scale_width)

    c2_emoji = "🟢" if c2 >= o2 else "🔴"
    c1_emoji = "🟢" if c1 >= o1 else "🔴"
    c0_emoji = "🟢" if c0 >= o0 else "🔴"

    c2_color = GRN if c2 >= o2 else RED
    c1_color = GRN if c1 >= o1 else RED
    c0_color = GRN if c0 >= o0 else RED

    rows = [
        (c2, c2_emoji, f" C2-{c2:.2f}", "█", c2_color),
        (c1, c1_emoji, f" C1-{c1:.2f}", "█", c1_color),
        (c0, c0_emoji, f" C0-{c0:.2f}", "█", c0_color)
    ]
    rows.sort(key=lambda item: item[0], reverse=True)

    print(f"\n{_pad_line_to_42(header_text, YLW, RST)}")
    
    for val, emoji, label, marker, color in rows:
        left_label = f" {emoji}{label} : "
        bar_graph = f"[{get_clean_bar(val, marker)}]"
        combined_visible = f"{left_label}{bar_graph}"
        print(_pad_line_to_42(combined_visible, color, RST))
        
    sig_emoji = "🔼" if entry in ["BUY", "BULL"] else "🔽"
    signal_text = f" {sig_emoji} SIGNAL VERIFIED: {entry}"
    print(_pad_line_to_42(signal_text, YLW, RST))
    print(f"{_pad_line_to_42(border_text, YLW, RST)}")

def apply_mode_5_transformation(df):
    """Applies the dense hybrid multi-model transformation matrix correctly without column leakage."""
    if df.empty: return df
    
    # Extract values into independent numpy arrays to prevent sequential overwriting bugs
    o = df['Open'].to_numpy(copy=True)
    h = df['High'].to_numpy(copy=True)
    l = df['Low'].to_numpy(copy=True)
    c = df['Close'].to_numpy(copy=True)
    n = len(df)

    # Matrix Model A: Heikin-Ashi Smooth Calculation
    ha_c = (o + h + l + c) / 4
    ha_o = np.zeros_like(o)
    
    if n > 0: 
        ha_o[0] = (o[0] + c[0]) / 2  # Set historical anchor exclusively at index 0
        
    for i in range(1, n):
        ha_o[i] = (ha_o[i-1] + ha_c[i-1]) / 2
        
    ha_h = np.maximum(h, np.maximum(ha_o, ha_c))
    ha_l = np.minimum(l, np.minimum(ha_o, ha_c))

    # Matrix Model B: Open-Close Median
    oc2 = (o + c) / 2

    # Matrix Model C: Momentum Boundaries (Shifted Closed Candlesticks)
    c1 = np.copy(c)
    c1[1:] = c[:-1]

    # Initialize separate dataframe instance to prevent cross-contamination
    transformed_df = df.copy()
    
    # Assign newly calculated values simultaneously across columns
    transformed_df['Open'] = (o + ha_o + oc2 + c1) / 4
    transformed_df['High'] = (h + ha_h + oc2 + c) / 4
    transformed_df['Low'] = (l + ha_l + oc2 + c1) / 4
    transformed_df['Close'] = (c + ha_c + oc2 + c) / 4
    return transformed_df

def calculate_no_repaint_signals(df):
    """ Evaluates trends directly from the live Mode 5 running candle. """
    if df.empty or len(df) < 2:
        return 0.0, "NONE"

    opens = df['Open'].to_numpy()
    closes = df['Close'].to_numpy()

    live_ltp = float(closes[-1])

    running_is_bullish = closes[-1] >= opens[-1]
    previously_confirmed_is_bullish = closes[-2] >= opens[-2]

    # Logic to evaluate the transition state of the matrix
    if running_is_bullish and not previously_confirmed_is_bullish:
        signal = "BUY"   
    elif not running_is_bullish and previously_confirmed_is_bullish:
        signal = "SELL"  
    elif running_is_bullish:
        signal = "BULL"  
    else:
        signal = "BEAR"  

    has_three = len(closes) >= 3
    _print_console_bar(
        c2=closes[-3] if has_three else closes[-2], 
        c1=closes[-2], 
        c0=closes[-1],
        o2=opens[-3] if has_three else opens[-2], 
        o1=opens[-2], 
        o0=opens[-1],
        entry=signal, 
        exit_sig="NONE"
    )

    return live_ltp, signal

def export_chart_json(df, lookback=42):
    """ Cleans old files from prior days and logs the new calculation history matrix. """
    try:
        if df.empty: return
        
        if os.path.exists(JSON_OUTPUT):
            tz_context = pytz.timezone(TIMEZONE)
            current_date_ist = datetime.now(tz_context).date()
            file_mtime = os.path.getmtime(JSON_OUTPUT)
            file_date_ist = datetime.fromtimestamp(file_mtime, tz_context).date()
            if file_date_ist < current_date_ist:
                os.remove(JSON_OUTPUT)

        df_target = df.copy()
        o = df_target['Open']
        h = df_target['High']
        l = df_target['Low']
        c = df_target['Close']
        c1 = df_target['Close'].shift(1)

        e1 = c
        e2 = (c1 + c) / 2
        e3 = (c + o) / 2
        e4 = (o + h + l + c) / 4
        
        df_target['P_Master'] = (e1 + e2 + e3 + e4) / 4
        
        output = []
        for idx, row in df_target.iterrows():
            p_val = float(row["P_Master"]) if not np.isnan(row["P_Master"]) else float(row["Close"])
            output.append({
                "time": str(idx),
                "close": float(row["Close"]),
                "p_master": p_val,
                "st": float(row["Close"]),  
                "st_trend": "BULL" if row["Close"] >= row["Open"] else "BEAR"
            })
            
        current_len = len(output)
        if current_len < lookback:
            padding_needed = lookback - current_len
            first_candle = output[0]  
            padding_list = [first_candle.copy() for _ in range(padding_needed)]
            output = padding_list + output
        else:
            output = output[-lookback:]

        with open(JSON_OUTPUT, "w") as f:
            json.dump(output, f, indent=4)
            
    except Exception as e:
        print(f"Error exporting JSON: {str(e)}")

def get_all_data():
    """ Fetches recent ticker bars, computes transformations, updates outputs, and provides operational summaries. """
    try:
        raw_df = dispatch_mode(
            "fetch_yf_data",
            lambda **_: yf.download(tickers=TICKER, period="2d", interval="1m", progress=False),
            target_rows=60,
            interval="1m",
            timezone=TIMEZONE,
        )
        if raw_df.empty:
            return {"entry": "NONE", "price": 0.0}

        # Format multi-level columns if explicitly returned by the API
        if isinstance(raw_df.columns, pd.MultiIndex):
            raw_df.columns = raw_df.columns.get_level_values(0)

        # Process mathematical state arrays and update structural records
        transformed_df = apply_mode_5_transformation(raw_df)
        ltp, signal = calculate_no_repaint_signals(transformed_df)
        export_chart_json(transformed_df)

        return {"entry": signal, "price": ltp}
    except Exception as e:
        print(f"Error in structural state acquisition pipeline: {str(e)}")
        return {"entry": "NONE", "price": 0.0}

if __name__ == "__main__":
    # Internal baseline loop debugging layer execution context
    print("Testing data ingestion systems engine execution pass...")
    engine_data = get_all_data()
    print(f"Result returned to entry script: {engine_data}")
