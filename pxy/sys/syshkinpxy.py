# syshkinpxy.py
import pandas as pd
from sysdthapxy import get_ha_data
from colorama import Fore, Style, init

# Initialize Colorama
init(autoreset=True)

# -------------------- HA Flip Detection --------------------
def detect_ha_flip_signal(df=None):
    if df is None or df.empty:
        return "", 0, 0, 0  # Return zeros explicitly

    # Heikin-Ashi calculation
    ha_close = (df['Open'] + df['High'] + df['Low'] + df['Close']) / 4
    ha_open = (df['Open'].shift(1) + df['Close'].shift(1)) / 2

    # Generate last 3-4 candle colors
    n = min(4, len(ha_close))
    colors = ['🟩' if ha_close.iloc[i] >= ha_open.iloc[i] else '🟥' for i in range(-n, 0)]

    current_color = colors[-1]
    last_closed_color = colors[-2] if len(colors) >= 2 else current_color

    # ---------------- Detect signal ----------------
    signal = None  # Default to None, no assumption

    # Explicit conditions
    if last_closed_color == '🟥' and current_color == '🟩':
        signal = "BUY"
    elif last_closed_color == '🟩' and current_color == '🟥':
        signal = "SELL"
    elif len(colors) >= 3:
        last_two = colors[-3:-1]
        if last_two == ['🟩', '🟩']:
            signal = "BULL"
        elif last_two == ['🟥', '🟥']:
            signal = "BEAR"

    if signal is None:
        signal = "NONE"  # Explicit final condition, not a generic else

    # ---------------- Past depth (previous streak) ----------------
    past_depth = 1
    prev_color = colors[-2] if len(colors) >= 2 else current_color
    for c in reversed(colors[:-1]):
        if c == prev_color:
            past_depth += 1
        else:
            break

    # ---------------- Current CE/PE depth (active streak) ----------------
    ce_depth = pe_depth = 1
    current_depth = 1
    for c in reversed(colors):
        if c == current_color:
            current_depth += 1
        else:
            break

    if current_color == '🟩':
        ce_depth = current_depth
    elif current_color == '🟥':
        pe_depth = current_depth

    # Return exactly 4 values
    return signal, past_depth, ce_depth, pe_depth


# -------------------- Self-runnable test --------------------
if __name__ == "__main__":
    # Assume you already have your DataFrame `df` from elsewhere
    # e.g., df = get_ha_data("AAPL") or passed from your main loop

    if __name__ == "__main__":
    # Call without passing any DataFrame
    signal, past_depth, ce_depth, pe_depth = detect_ha_flip_signal()

    # Print results
    print(f"Signal: {signal}, Past Depth: {past_depth}, CE Depth: {ce_depth}, PE Depth: {pe_depth}")


