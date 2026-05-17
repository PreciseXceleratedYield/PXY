from colorama import Fore, Style, init
import pandas as pd

init(autoreset=True)
WIDTH = 42

# ---------------- DETERMINISTIC VISUAL ENGINE (MODIFIED FOR WICK CHAR) ----------------
def build_candle_bar(o, h, l, c, width=WIDTH):
    o, h, l, c = map(float, (o, h, l, c))
    rng = h - l
    if rng == 0:
        rng = 1e-9
    lower = max(0.0, min(1.0, (min(o, c) - l) / rng))
    upper = max(0.0, min(1.0, (h - max(o, c)) / rng))
    body = max(0.0, 1.0 - lower - upper)
    lower_len = int(lower * width)
    body_len = int(body * width)
    upper_len = width - lower_len - body_len
    if body_len < 1:
        body_len = 1
    if lower_len + body_len > width:
        lower_len = width - body_len
    upper_len = width - lower_len - body_len
    bar = ""
    # lower wick (Using ━)
    bar += Fore.LIGHTBLACK_EX + "━" * lower_len
    # body (Using █)
    if c > o:
        bar += Fore.GREEN + "█" * body_len
    elif o > c:
        bar += Fore.RED + "█" * body_len
    else:
        bar += Fore.YELLOW + "█" * body_len
    # upper wick (Using ━)
    bar += Fore.LIGHTBLACK_EX + "━" * upper_len
    return bar + Style.RESET_ALL

# ---------------- 42-MIN ROLLING API (MIDPOINT OPEN MODIFIED) ----------------
def get_bos_bar(df):
    try:
        if df is None or len(df) < 42:
            return Fore.LIGHTBLACK_EX + "━" * WIDTH + Style.RESET_ALL, "0.00"
            
        # 1. Capture Cumulative 42-minute boundaries
        window = df.iloc[-42:]
        h_42 = float(window['High'].max())
        l_42 = float(window['Low'].min())
        c_42 = float(window.iloc[-1]['Close'])  # Live current close price
        
        # Override the first open with the true High-Low window midpoint
        o_42 = (h_42 + l_42) / 2.0
        
        # 2. Build the visual bar using modified midpoint open parameters
        visual_bar = build_candle_bar(o_42, h_42, l_42, c_42)
        
        # 3. Calculate 42-Period Simple Moving Average on Close Prices
        sma_42 = float(window['Close'].mean())
        
        # 4. EXACT PINE SCRIPT MATCH: (SMA42 + LIVE) / 2
        # No more weights (*2). Now uses a pure 50/50 split midpoint engine.
        bos_value = (sma_42 + c_42) / 2.0
        
        bos_str = f"{bos_value:.2f}"
        return visual_bar, bos_str
        
    except Exception:
        return Fore.LIGHTBLACK_EX + "━" * WIDTH + Style.RESET_ALL, "ERR"





