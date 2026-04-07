# syshkinpxy.py

# -------------------- CONFIG SWITCH --------------------
candle = "ha"  # set to "ha" or "cv"
candle = candle.lower()

if candle == "ha":
    from sysdthapxy import get_ha_data
elif candle == "cv":
    from sysdtcvpxy import get_ha_data
else:
    raise ValueError(f"Invalid candle type: {candle}. Must be 'ha' or 'cv'.")

import pandas as pd
from colorama import Fore, Style, init

# Initialize Colorama
init(autoreset=True)


# -------------------- FLIP SIGNAL DETECTION --------------------
def detect_ha_flip_signal(df=None):
    """
    Detects live flip signals and trend continuations based on c1/c2 comparison.
    Works for both HA and CV modes.
    Returns:
        signal    : "BUY"/"SELL"/"BULL"/"BEAR"/"NONE"
        past_depth: depth of previous color
        ce_depth  : depth for CE
        pe_depth  : depth for PE
    """

    # ---------------- FETCH DATA ----------------
    if df is None:
        c1_close, c2_close, c_color, df = get_ha_data()
    else:
        c1_close, c2_close, c_color, df = get_ha_data(df=df)

    # ---------------- VALIDATION ----------------
    if df is None or df.empty or c_color is None or len(c_color) < 2:
        return "NONE", 1, 1, 1

    # ---------------- LAST COLORS ----------------
    n = min(5, len(c_color))
    colors = [c_color.iloc[i] for i in range(-n, 0)]
    current_color = colors[-1]
    prev_color = colors[-2]

    # ---------------- CURRENT DEPTH ----------------
    current_depth = 0
    for c in reversed(colors):
        if c == current_color:
            current_depth += 1
        else:
            break
    current_depth = max(current_depth, 1)

    # ---------------- PAST DEPTH ----------------
    past_depth = 0
    for c in reversed(colors[:-1]):
        if c == prev_color:
            past_depth += 1
        else:
            break
    past_depth = max(past_depth, 1)

    # ---------------- SIGNAL LOGIC ----------------
    signal = "NONE"

    if current_color == "none" or prev_color == "none":
        signal = "NONE"
    elif prev_color == "red" and current_color == "green":
        if past_depth >= 1 and current_depth == 1:
            signal = "BUY"
    elif prev_color == "green" and current_color == "red":
        if past_depth >= 1 and current_depth == 1:
            signal = "SELL"
    elif prev_color == "green" and current_color == "green":
        if len(colors) >= 3 and colors[-3] == "green":
            signal = "BULL"
    elif prev_color == "red" and current_color == "red":
        if len(colors) >= 3 and colors[-3] == "red":
            signal = "BEAR"

    # ---------------- CE / PE DEPTH ----------------
    ce_depth = 1
    pe_depth = 1
    if current_color == "green":
        ce_depth = current_depth
    elif current_color == "red":
        pe_depth = current_depth

    return signal, past_depth, ce_depth, pe_depth


# -------------------- SELF TEST --------------------
if __name__ == "__main__":

    signal, past_depth, ce_depth, pe_depth = detect_ha_flip_signal()

    print("\n" + "="*60)
    print("FLIP SIGNAL DEBUG (ULTRA STRICT + FORMING CANDLE)")
    print("="*60)

    # Color mapping
    sig_color = {
        "BUY": Fore.GREEN,
        "SELL": Fore.RED,
        "BULL": Fore.CYAN,
        "BEAR": Fore.MAGENTA
    }.get(signal, Fore.WHITE)

    print(f"Signal     : {sig_color}{signal}{Style.RESET_ALL}")
    print(f"Past Depth : {past_depth}")
    print(f"CE Depth   : {ce_depth}")
    print(f"PE Depth   : {pe_depth}")
