# syshkinpxy.py
import pandas as pd
from sysdthapxy import get_ha_data
from colorama import Fore, Style, init

# Initialize Colorama
init(autoreset=True)

# -------------------- HA Flip Detection --------------------
def detect_ha_flip_signal(df=None):
    if df is None or df.empty:
        return "", "None", "None", pd.Series([0])

    # Heikin-Ashi calculation
    ha_close = (df['Open'] + df['High'] + df['Low'] + df['Close']) / 4
    ha_open = (df['Open'].shift(1) + df['Close'].shift(1)) / 2

    # Generate last 3-4 candle colors using emojis
    colors = []
    n = min(4, len(ha_close))
    for i in range(-n, 0):
        colors.append('🟩' if ha_close.iloc[i] >= ha_open.iloc[i] else '🟥')

    current_color = 'Bull' if colors[-1] == '🟩' else 'Bear'
    last_closed_color = 'Bull' if colors[-2] == '🟩' else 'Bear'

    # ---------------- Detect signal ----------------
    if last_closed_color == 'Bear' and current_color == 'Bull':
        signal = "BUY"
    elif last_closed_color == 'Bull' and current_color == 'Bear':
        signal = "SELL"
    else:
        # Check last two colors for streak
        if len(colors) >= 3:
            last_two = colors[-3:-1]
            if last_two == ['🟩', '🟩']:
                signal = "BULL"
            elif last_two == ['🟥', '🟥']:
                signal = "BEAR"
            else:
                signal = "NONE"
        else:
            signal = "NONE"

    # ---------------- Past depth (previous color streak) ----------------
    past_depth = 1
    prev_color = colors[-2]
    for c in reversed(colors[:-1]):
        if c == prev_color:
            past_depth += 1
        else:
            break

    # ---------------- Current CE/PE depth (active streak) ----------------
    ce_depth = pe_depth = 1
    curr_color = colors[-1]
    current_depth = 1
    for c in reversed(colors):
        if c == curr_color:
            current_depth += 1
        else:
            break

    if curr_color == '🟩':
        ce_depth = current_depth
    else:
        pe_depth = current_depth

    # Return exactly 4 values to match your main loop
    return signal, past_depth, ce_depth, pe_depth


# -------------------- Self-runnable test --------------------
if __name__ == "__main__":
    import yfinance as yf

    # Example fetch (replace with your df source)
    df = yf.download("AAPL", period="5d", interval="1h")

    signal, past_depth, ce_depth, pe_depth = detect_ha_flip_signal(df)

    # Color coding
    if signal in ["BUY", "BULL"]:
        color = Fore.GREEN
    elif signal in ["SELL", "BEAR"]:
        color = Fore.RED
    else:
        color = Fore.YELLOW

    # Labels + values
    left_text = f"{color}Hkin:{signal}{Style.RESET_ALL}"
    middle_text = f"{color}Past:{past_depth}{Style.RESET_ALL}"
    right_text = f"{color}CE:{ce_depth} PE:{pe_depth}{Style.RESET_ALL}"

    # Compute spacing for total width = 42
    total_width = 42
    plain_left = f"Hkin:{signal}"  # length without color codes
    plain_middle = f"Past:{past_depth}"
    plain_right = f"CE:{ce_depth} PE:{pe_depth}"
    space_width = total_width - len(plain_left) - len(plain_middle) - len(plain_right)
    spacing = " " * max(space_width, 1)

    # Print single line
    print(left_text + middle_text + spacing + right_text)
