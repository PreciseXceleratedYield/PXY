# _sgnl.py
import os
import warnings
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
    rows.sort(key=lambda item: item[0], reverse=True)

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
    Evaluates trends directly from CLOSED, FIXED 1-minute Mode 5 candles.
    Completely prevents re-painting by comparing index -2 and index -3.
    """
    if df.empty or len(df) < 3:
        return 0.0, "NONE"

    opens = df['Open'].to_numpy()
    closes = df['Close'].to_numpy()

    # The actual order execution price is taken from the latest live tick (Index -1)
    live_ltp = float(closes[-1])

    # --- STRICT NO-REPAINT CLOSED CANDLE BOUNDARIES (1-MIN TIMEFRAME) ---
    # Confirmed Last Closed Candle (Index -2)
    confirmed_is_bullish = closes[-2] >= opens[-2]
    
    # Confirmed Prior Closed Candle (Index -3)
    previously_confirmed_is_bullish = closes[-3] >= opens[-3]

    # --- THE ABSOLUTE FLIP SIGNAL MATRIX ---
    if confirmed_is_bullish and not previously_confirmed_is_bullish:
        signal = "BUY"   # The closed 1-min candle flipped Bearish -> Bullish
    elif not confirmed_is_bullish and previously_confirmed_is_bullish:
        signal = "SELL"  # The closed 1-min candle flipped Bullish -> Bearish
    elif confirmed_is_bullish:
        signal = "BULL"  # Trend remains locked in a Green state
    else:
        signal = "BEAR"  # Trend remains locked in a Red state

    # --- RENDER VISUAL PRINT BAR MATRIX ---
    _print_console_bar(
        c2=closes[-3], c1=closes[-2], c0=closes[-1],
        o2=opens[-3], o1=opens[-2], o0=opens[-1],
        entry=signal, exit_sig="NONE"
    )

    return live_ltp, signal

def get_all_data():
    """
    Downloads strictly 1 day of 1-minute bars straight from yfinance.
    Applies Mode 5 and maps out the verified no-repaint trend flips.
    """
    try:
        # Fetching strictly today's 1-minute tracking profile
        ticker_obj = yf.Ticker(TICKER)
        df = ticker_obj.history(period="1d", interval="1m")
        
        if df.empty:
            empty_msg = "⚠️ Data Stream Empty: Check Feed"
            print(_pad_line_to_42(empty_msg, "\033[93m", "\033[0m"))
            return {"entry": "NONE", "price": 0.0}

        df.dropna(inplace=True)
        df.index = pd.to_datetime(df.index).tz_convert(TIMEZONE) # IST Timezone Lock

        # Process historical completed rows via Mode 5 transformation matrix
        transformed_df = apply_mode_5_transformation(df.copy())
        ltp, signal = calculate_no_repaint_signals(transformed_df)
        
        return {"entry": signal, "price": ltp}

    except Exception as e:
        err_msg = f"❌ Signal Error: {str(e)[:24]}"
        print(_pad_line_to_42(err_msg, "\033[91m", "\033[0m"))
        return {"entry": "NONE", "price": 0.0}

if __name__ == "__main__":
    test_msg = f"📡 Scanning Market Feed: {TICKER}"
    print(_pad_line_to_42(test_msg, "\033[93m", "\033[0m"))
    get_all_data()

