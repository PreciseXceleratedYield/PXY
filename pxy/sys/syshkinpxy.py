# syshkinpxy.py

import pandas as pd
from sysdthapxy import get_ha_data
from colorama import Fore, Style, init

# Initialize Colorama
init(autoreset=True)


# -------------------- HA Flip Detection --------------------
def detect_ha_flip_signal(df=None):

    # ---------------- FETCH HA DATA ----------------
    ha_close, ha_open, ha_color, df = get_ha_data(df=df)

    # ---------------- VALIDATION ----------------
    if df is None:
        return "NONE", 1, 1, 1
    elif df.empty:
        return "NONE", 1, 1, 1
    elif ha_color is None:
        return "NONE", 1, 1, 1
    elif len(ha_color) < 2:
        return "NONE", 1, 1, 1
    else:
        pass

    # ---------------- GET LAST COLORS (INCLUDING FORMING) ----------------
    n = min(5, len(ha_color))
    colors = [ha_color.iloc[i] for i in range(-n, 0)]

    current_color = colors[-1]      # FORMING candle
    prev_color = colors[-2]         # LAST CLOSED candle

    # ---------------- CURRENT DEPTH ----------------
    current_depth = 0
    for c in reversed(colors):
        if c == current_color:
            current_depth += 1
        else:
            break

    if current_depth <= 0:
        current_depth = 1

    # ---------------- PAST DEPTH ----------------
    past_depth = 0
    for c in reversed(colors[:-1]):
        if c == prev_color:
            past_depth += 1
        else:
            break

    if past_depth <= 0:
        past_depth = 1

    # ---------------- SIGNAL DETECTION (ULTRA STRICT + EXCLUSIVE) ----------------

    # ---- CASE 1: INVALID STATES ----
    if current_color == "none":
        signal = "NONE"

    elif prev_color == "none":
        signal = "NONE"

    # ---- CASE 2: TRUE LIVE FLIP ----
    elif prev_color == "red" and current_color == "green":

        if past_depth >= 1 and current_depth == 1:
            signal = "BUY"

        elif past_depth >= 1 and current_depth > 1:
            signal = "NONE"

        else:
            signal = "NONE"

    elif prev_color == "green" and current_color == "red":

        if past_depth >= 1 and current_depth == 1:
            signal = "SELL"

        elif past_depth >= 1 and current_depth > 1:
            signal = "NONE"

        else:
            signal = "NONE"

    # ---- CASE 3: TREND CONTINUATION ----
    elif prev_color == "green" and current_color == "green":

        if len(colors) < 3:
            signal = "NONE"

        elif colors[-3] == "green":
            signal = "BULL"

        elif colors[-3] == "red":
            signal = "NONE"

        elif colors[-3] == "none":
            signal = "NONE"

        else:
            signal = "NONE"

    elif prev_color == "red" and current_color == "red":

        if len(colors) < 3:
            signal = "NONE"

        elif colors[-3] == "red":
            signal = "BEAR"

        elif colors[-3] == "green":
            signal = "NONE"

        elif colors[-3] == "none":
            signal = "NONE"

        else:
            signal = "NONE"

    # ---- CASE 4: EXPLICIT FALLBACK ----
    elif current_color in ["green", "red"]:
        signal = "NONE"

    else:
        signal = "NONE"

    # ---------------- CE / PE DEPTH ----------------
    ce_depth = 1
    pe_depth = 1

    if current_color == "green":
        ce_depth = current_depth
        pe_depth = 1

    elif current_color == "red":
        pe_depth = current_depth
        ce_depth = 1

    elif current_color == "none":
        ce_depth = 1
        pe_depth = 1

    else:
        ce_depth = 1
        pe_depth = 1

    # ---------------- FINAL RETURN ----------------
    return signal, past_depth, ce_depth, pe_depth


# -------------------- SELF TEST --------------------
if __name__ == "__main__":

    signal, past_depth, ce_depth, pe_depth = detect_ha_flip_signal()

    print("\n" + "="*60)
    print("HA FLIP DEBUG (ULTRA STRICT + FORMING CANDLE)")
    print("="*60)

    # Color mapping
    if signal == "BUY":
        sig_color = Fore.GREEN
    elif signal == "SELL":
        sig_color = Fore.RED
    elif signal == "BULL":
        sig_color = Fore.CYAN
    elif signal == "BEAR":
        sig_color = Fore.MAGENTA
    else:
        sig_color = Fore.WHITE

    print(f"Signal     : {sig_color}{signal}{Style.RESET_ALL}")
    print(f"Past Depth : {past_depth}")
    print(f"CE Depth   : {ce_depth}")
    print(f"PE Depth   : {pe_depth}")
