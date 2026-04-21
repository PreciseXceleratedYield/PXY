# ==================================================
# syshkinpxy_aligned.py (LIVE MODE - RUNNING CANDLE INCLUDED)
# ==================================================

import pandas as pd
from sysdthapxy import get_ha_data
from colorama import Fore, Style, init

init(autoreset=True)

def detect_ha_flip_signal(df=None, last_n=21):
    """
    Detect HA flip signals aligned exactly with depth chart.
    LIVE MODE: Includes running candle in all calculations.
    Returns: signal, past_depth, ce_depth, pe_depth
    """

    ha_close, ha_open, ha_color, df = get_ha_data(df=df)

    # Validation
    if df is None or df.empty or ha_color is None or len(ha_color) < 2:
        return "NA", 1, 1, 1

    # ==================================================
    # 🔥 LIVE MODE: INCLUDE RUNNING CANDLE
    # (only remove invalid values like "none")
    # ==================================================
    colors_full = ha_color.tolist()

    # Keep ONLY valid HA colors (do NOT remove last candle)
    colors = [c for c in colors_full if c in ("green", "red")]

    if len(colors) < 2:
        return "NA", 1, 1, 1

    # Last N colors
    n = min(last_n, len(colors))
    colors_n = colors[-n:]

    current_color = colors_n[-1]
    prev_color = colors_n[-2]

    # ==================================================
    # CURRENT DEPTH (LIVE)
    # ==================================================
    current_depth = 0
    for c in reversed(colors_n):
        if c == current_color:
            current_depth += 1
        else:
            break

    current_depth = max(current_depth, 1)

    # ==================================================
    # PAST DEPTH (LIVE)
    # ==================================================
    current_color = colors[-1]

    current_streak_start = len(colors) - 1
    for i in reversed(range(len(colors) - 1)):
        if colors[i] != current_color:
            current_streak_start = i + 1
            break

    prev_color = colors[current_streak_start - 1] if current_streak_start > 0 else "none"

    past_depth = 0
    for i in reversed(range(current_streak_start)):
        if colors[i] == prev_color:
            past_depth += 1
        else:
            break

    past_depth = max(past_depth, 1)

    # ==================================================
    # SIGNAL LOGIC (UNCHANGED)
    # ==================================================
    if current_color == "none" or prev_color == "none":
        signal = "NA"

    elif prev_color == "red" and current_color == "green":
        signal = "BUY" if current_depth == 1 else "NA"

    elif prev_color == "green" and current_color == "red":
        signal = "SELL" if current_depth == 1 else "NA"

    elif prev_color == "green" and current_color == "green":
        signal = "BULL" if past_depth >= 2 else "NA"

    elif prev_color == "red" and current_color == "red":
        signal = "BEAR" if past_depth >= 2 else "NA"

    else:
        signal = "NA"

    # ==================================================
    # CE / PE DEPTH (LIVE)
    # ==================================================
    ce_depth = current_depth if current_color == "green" else 1
    pe_depth = current_depth if current_color == "red" else 1

    # Format past depth label
    if current_streak_start > 0:
        streak_color = colors[current_streak_start - 1]
        past_depth = f"CE{past_depth}" if streak_color == "green" else f"PE{past_depth}" if streak_color == "red" else "NA"
    else:
        past_depth = "NA"

    return signal, past_depth, ce_depth, pe_depth


# ---------------- SELF TEST ----------------
if __name__ == "__main__":
    signal, past_depth, ce_depth, pe_depth = detect_ha_flip_signal()

    print("\n" + "="*60)
    print("HA FLIP DEBUG (LIVE MODE - RUNNING CANDLE)")
    print("="*60)

    sig_color = {
        "BUY": Fore.GREEN,
        "SELL": Fore.RED,
        "BULL": Fore.CYAN,
        "BEAR": Fore.MAGENTA,
        "NA": Fore.WHITE
    }.get(signal, Fore.WHITE)

    print(f"Signal     : {sig_color}{signal}{Style.RESET_ALL}")
    print(f"Past Depth : {past_depth}")
    print(f"CE Depth   : {ce_depth}")
    print(f"PE Depth   : {pe_depth}")
