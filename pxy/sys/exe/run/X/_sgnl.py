# _sgnl.py
import os
import warnings
import json
from datetime import datetime
import pytz
import numpy as np
import pandas as pd
import yfinance as yf

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
        # Check if the character is an emoji/special symbol or circled number
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
    GRAY = "\033[90m"

    # Contextual header emoji depending on active signal matrix state
    header_emoji = "🐂" if entry in ["BUY", "BULL"] else "🐻"
    header_text = f"{header_emoji} GEOMETRIC MATRIX ENGINE"
    border_text = "==========================================" # 42 chars

    min_val = min(c2, c1, c0) - 2
    max_val = max(c2, c1, c0) + 2
    scale_width = 23

    def get_clean_bar(val, marker="█"):
        pos = int(((val - min_val) / (max_val - min_val)) * scale_width)
        pos = max(1, min(pos, scale_width))
        return (marker * pos).ljust(scale_width)

    # Pick dynamic status emojis for each completed row
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
    rows.sort(key=lambda item: item, reverse=True)

    # Print 42-width Header
    print(f"\n{_pad_line_to_42(header_text, YLW, RST)}")
    
    # Print 42-width Data Rows
    for val, emoji, label, marker, color in rows:
        left_label = f" {emoji}{label} : "
        bar_graph = f"[{get_clean_bar(val, marker)}]"
        combined_visible = f"{left_label}{bar_graph}"
        print(_pad_line_to_42(combined_visible, color, RST))
        
    # Print 42-width Signal Confirmation Banner
    sig_emoji = "🔼" if entry in ["BUY", "BULL"] else "🔽"
    signal_text = f" {sig_emoji} SIGNAL VERIFIED: {entry}"
    print(_pad_line_to_42(signal_text, YLW, RST))

    # Print 42-width Footer Border
    print(f"{_pad_line_to_42(border_text, YLW, RST)}")

def apply_mode_5_transformation(df):
    """Applies the dense hybrid multi-model transformation matrix."""
    if df.empty: return df
    
    o = df['Open'].to_numpy()
    h = df['High'].to_numpy()
    l = df['Low'].to_numpy()
    c = df['Close'].to_numpy()
    n = len(df)

    # Matrix Model A: Heikin-Ashi Smooth Calculation
    ha_c = (o + h + l + c) / 4
    ha_o = np.zeros_like(o)
    if n > 0: ha_o = (o + c) / 2 # TARGET INDEX 0 FIXED
    for i in range(1, n):
        ha_o[i] = (ha_o[i-1] + ha_c[i-1]) / 2
    ha_h = np.maximum(h, np.maximum(ha_o, ha_c))
    ha_l = np.minimum(l, np.minimum(ha_o, ha_c))

    # Matrix Model B: Open-Close Median
    oc2 = (o + c) / 2

    # Matrix Model C: Momentum Boundaries
    c1 = np.copy(c)
    c1[1:] = c[:-1]

    # Uniform merging matrix block layer
    df['Open'] = (o + ha_o + oc2 + c1) / 4
    df['High'] = (h + ha_h + oc2 + c) / 4
    df['Low'] = (l + ha_l + oc2 + c1) / 4
    df['Close'] = (c + ha_c + oc2 + c) / 4
    return df

def calculate_no_repaint_signals(df):
    """
    Evaluates trends directly from the RUNNING (Live) 1-minute Mode 5 candle.
    Note: Signals can fluctuate (repaint) dynamically until the candle closes.
    """
    if df.empty or len(df) < 2:
        return 0.0, "NONE"

    opens = df['Open'].to_numpy()
    closes = df['Close'].to_numpy()

    # The actual order execution price is taken from the latest live tick (Index -1)
    live_ltp = float(closes[-1])

    # --- LIVE RUNNING CANDLE BOUNDARIES (1-MIN TIMEFRAME) ---
    # Current Running Candle (Index -1)
    running_is_bullish = closes[-1] >= opens[-1]
    
    # Confirmed Prior Closed Candle (Index -2)
    previously_confirmed_is_bullish = closes[-2] >= opens[-2]

    # --- THE RUNNING FLIP SIGNAL MATRIX ---
    if running_is_bullish and not previously_confirmed_is_bullish:
        signal = "BUY"   # The live running candle turned Bearish -> Bullish
    elif not running_is_bullish and previously_confirmed_is_bullish:
        signal = "SELL"  # The live running candle turned Bullish -> Bearish
    elif running_is_bullish:
        signal = "BULL"  # Running candle continues the green trend state
    else:
        signal = "BEAR"  # Running candle continues the red trend state

    # --- RENDER VISUAL PRINT BAR MATRIX ---
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
    """ Cleans old files from prior days immediately and writes fresh padded processed Mode 5 data. """
    try:
        if df.empty: return
        
        # --- CRITICAL STALE FILE CLEANUP INTERFACE ---
        if os.path.exists(JSON_OUTPUT):
            tz_context = pytz.timezone(TIMEZONE)
            current_date_ist = datetime.now(tz_context).date()
            
            # Extract file modification timestamp date window
            file_mtime = os.path.getmtime(JSON_OUTPUT)
            file_date_ist = datetime.fromtimestamp(file_mtime, tz_context).date()
            
            # If the local JSON belongs to a different day, completely wipe it out
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
            
        # --- TODAY-ONLY BACKFILL LOGIC ---
        current_len = len(output)
        if current_len < lookback:
            padding_needed = lookback - current_len
            first_candle = output[0]  # Grab the very first 09:15 AM candle node
            
            # Create duplicates to pad the top of the array
            padding_list = [first_candle.copy() for _ in range(padding_needed)]
            output = padding_list + output
        else:
            # If we already have 42+ bars, just take the last 42 as normal
            output = output[-lookback:]
            
        with open(JSON_OUTPUT, "w") as f:
            json.dump(output, f, indent=4)
            
    except Exception as e:
        print(f"Error exporting JSON: {e}")

def get_all_data():
    """
    Saves and exposes data to the _entry.py execution script 
    by extracting the latest trend state out of the exported JSON node.
    """
    try:
        if not os.path.exists(JSON_OUTPUT):
            return {"entry": "NONE", "price": 0.0}
            
        with open(JSON_OUTPUT, "r") as f:
            data_list = json.load(f)
            
        if not data_list or len(data_list) == 0:
            return {"entry": "NONE", "price": 0.0}
            
        # Extract the latest live processed candle entry 
        latest_node = data_list[-1]
        
        return {
            "entry": latest_node.get("st_trend", "NONE"),
            "price": latest_node.get("close", 0.0)
        }
    except Exception:
        return {"entry": "NONE", "price": 0.0}

