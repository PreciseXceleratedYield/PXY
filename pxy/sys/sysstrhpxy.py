# sysstrhpxy.py
import pandas as pd
from colorama import Fore, Style, init
from sysdthapxy import get_ha_data
from syskatrpxy import calculate_atr
from syssadxpxy import calculate_adx

init(autoreset=True)
TOTAL_WIDTH = 42

def get_candle_strength_line(df=None):
    ha_close, ha_open, ha_color, df = get_ha_data(df=df)
    """
    Returns a formatted 42-character line with color,
    plus strength label and numeric score.
    """
    ha_close, ha_open, ha_color, df = get_ha_data()

    if df is None or len(df) == 0:
        strength_label = "CE Weak"
        score_value = 0.0
        color = Fore.GREEN
    else:
        current_color = ha_color.iloc[-1]

        # Determine CE / PE strength
        ha_high = pd.concat([df['High'], ha_open, ha_close], axis=1).max(axis=1)
        ha_low  = pd.concat([df['Low'], ha_open, ha_close], axis=1).min(axis=1)
        recent_colors = ha_color.iloc[-3:]
        recent_high   = ha_high.iloc[-3:]
        recent_low    = ha_low.iloc[-3:]

        if current_color == "green":
            prev_highs = recent_high[:-1][recent_colors[:-1]=="green"]
            strength = "Strong" if len(prev_highs)>0 and recent_high.iloc[-1] > prev_highs.max() else "Weak"
            strength_label = f"CE:{strength}"
        else:
            prev_lows = recent_low[:-1][recent_colors[:-1]=="red"]
            strength = "Strong" if len(prev_lows)>0 and recent_low.iloc[-1] < prev_lows.min() else "Weak"
            strength_label = f"PE:{strength}"

        # Color selection
        if strength == "Strong":
            color = Fore.GREEN if "CE" in strength_label else Fore.RED
        else:
            color = Fore.YELLOW

        # Score calculation using ATR + ADX
        atr_series = calculate_atr(df)
        atr = atr_series.iloc[-1] if not pd.isna(atr_series.iloc[-1]) else 1.0
        adx = calculate_adx(df)
        candle_range = df['High'].iloc[-1] - df['Low'].iloc[-1]
        score_value = (candle_range / atr) * (adx / 100) if atr != 0 else 0.0

    # Build 42-character line
    left_text = f"{color}{strength_label}{Style.RESET_ALL}"
    right_text = f"{color}Score:{score_value:.2f}{Style.RESET_ALL}"
    plain_left = f"{strength_label}"
    plain_right = f"Score:{score_value:.2f}"
    space_width = TOTAL_WIDTH - len(plain_left) - len(plain_right)
    if space_width < 0:
        space_width = 1
    spacing = " " * space_width

    line = left_text + spacing + right_text
    return line, strength, score_value

# -------- Self-runnable print --------
if __name__ == "__main__":
    line, _, _ = get_candle_strength_line()
    print(line)
