from colorama import Fore, Style, init
import pandas as pd

init(autoreset=True)
WIDTH = 42

# ---------------- DETERMINISTIC VISUAL ENGINE (UNMODIFIED) ----------------
def build_candle_bar(o, h, l, c, width=WIDTH):
    o, h, l, c = map(float, (o, h, l, c))
    rng = h - l
    if rng == 0: rng = 1e-9

    lower = max(0.0, min(1.0, (min(o, c) - l) / rng))
    upper = max(0.0, min(1.0, (h - max(o, c)) / rng))
    body = max(0.0, 1.0 - lower - upper)

    lower_len = int(lower * width)
    body_len = int(body * width)
    upper_len = width - lower_len - body_len

    if body_len < 1: body_len = 1
    if lower_len + body_len > width:
        lower_len = width - body_len
    upper_len = width - lower_len - body_len

    bar = ""
    # lower wick
    bar += Fore.LIGHTBLACK_EX + "█" * lower_len
    # body
    if c > o:
        bar += Fore.GREEN + "█" * body_len
    elif o > c:
        bar += Fore.RED + "█" * body_len
    else:
        bar += Fore.YELLOW + "█" * body_len
    # upper wick
    bar += Fore.LIGHTBLACK_EX + "█" * upper_len
    
    return bar + Style.RESET_ALL

# ---------------- 42-MIN ROLLING API ----------------
def get_bos_bar(df):
    try:
        if df is None or len(df) < 42:
            return Fore.LIGHTBLACK_EX + "█" * WIDTH + Style.RESET_ALL, "0%"

        # 1. Capture Cumulative 42-minute OHLC
        window = df.iloc[-42:]
        o_42 = float(window.iloc[0]['Open'])    # Open of the 42nd minute ago
        h_42 = float(window['High'].max())      # Highest High of the 42-min window
        l_42 = float(window['Low'].min())       # Lowest Low of the 42-min window
        c_42 = float(window.iloc[-1]['Close'])  # Current Price

        # 2. Build the visual bar using your exact logic
        visual_bar = build_candle_bar(o_42, h_42, l_42, c_42)

        # 3. Calculate 1-99% Strength (Low-to-Close position)
        rng = h_42 - l_42
        if rng != 0:
            raw_val = round(((c_42 - l_42) / rng) * 100)
        else:
            raw_val = 50
        
        strength_pct = f"{max(1, min(99, raw_val))}%"

        return visual_bar, strength_pct

    except Exception:
        return Fore.LIGHTBLACK_EX + "█" * WIDTH + Style.RESET_ALL, "ERR%"



