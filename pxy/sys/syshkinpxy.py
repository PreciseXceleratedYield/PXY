# syshkinpxy_aligned.py

import pandas as pd
from sysdthapxy import get_ha_data
from colorama import Fore, Style, init

init(autoreset=True)

def detect_ha_flip_signal(df=None, last_n=21):
    """
    Detect HA flip signals aligned exactly with depth chart.
    Returns: signal, past_depth, ce_depth, pe_depth
    """
    ha_close, ha_open, ha_color, df = get_ha_data(df=df)

    # Validation
    if df is None or df.empty or ha_color is None or len(ha_color) < 2:
        return "NONE", 1, 1, 1

    # Last N colors (including forming)
    n = min(last_n, len(ha_color))
    colors = ha_color.iloc[-n:].tolist()

    current_color = colors[-1]
    prev_color = colors[-2]

    # Current depth: consecutive same-color bars from forming candle
    current_depth = 0
    for c in reversed(colors):
        if c == current_color:
            current_depth += 1
        else:
            break
    current_depth = max(current_depth, 1)

    # ---------------- PAST DEPTH (aligned to chart) ----------------
    past_depth = 0
    for c in reversed(colors[:-1]):   # look at all previous colors except current
        if c == prev_color:
            past_depth += 1
        else:
            break
    
    past_depth = max(past_depth, 1)  # ensure at least 1

    # Signal detection
    if current_color == "none" or prev_color == "none":
        signal = "NONE"
    elif prev_color == "red" and current_color == "green":
        signal = "BUY" if current_depth == 1 else "NONE"
    elif prev_color == "green" and current_color == "red":
        signal = "SELL" if current_depth == 1 else "NONE"
    elif prev_color == "green" and current_color == "green":
        signal = "BULL" if past_depth >= 2 else "NONE"
    elif prev_color == "red" and current_color == "red":
        signal = "BEAR" if past_depth >= 2 else "NONE"
    else:
        signal = "NONE"

    # CE / PE depth
    ce_depth = current_depth if current_color == "green" else 1
    pe_depth = current_depth if current_color == "red" else 1

    return signal, past_depth, ce_depth, pe_depth

# ---------------- SELF TEST ----------------
if __name__ == "__main__":
    signal, past_depth, ce_depth, pe_depth = detect_ha_flip_signal()
    print("\n" + "="*60)
    print("HA FLIP DEBUG (ALIGNED TO DEPTH CHART)")
    print("="*60)

    # Color mapping
    sig_color = {
        "BUY": Fore.GREEN,
        "SELL": Fore.RED,
        "BULL": Fore.CYAN,
        "BEAR": Fore.MAGENTA,
        "NONE": Fore.WHITE
    }.get(signal, Fore.WHITE)

    print(f"Signal     : {sig_color}{signal}{Style.RESET_ALL}")
    print(f"Past Depth : {past_depth}")
    print(f"CE Depth   : {ce_depth}")
    print(f"PE Depth   : {pe_depth}")
