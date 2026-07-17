# sysexitpxy.py
import pandas as pd
from syscnfgpxy import PARAMS  # Only TICKER will be used
from sysdtafpxy import fetch_yf_data
from colorama import Fore, Style, init

# Initialize Colorama
init(autoreset=True)

# -------------------- Hardcoded constants --------------------
ROLLING_WINDOW_MINUTES = 2.5  # previously from PARAMS
ROWS_PER_MINUTE = 1  # assuming 1-min candles
TOTAL_WIDTH = 42

# -------------------- Direction logic --------------------
def detect_raw_direction(df: pd.DataFrame) -> tuple:
    """
    Returns:
        (latest_price, direction)
    
    Raw Close direction logic:
    - UP: last closed candle < current candle
    - DOWN: last closed candle > current candle
    - NONE: if no movement or insufficient data
    """
    window_size = int(ROLLING_WINDOW_MINUTES * ROWS_PER_MINUTE)
    df_window = df.tail(window_size)

    closes = df_window['Close'].tolist()
    if len(closes) < 2:
        return (None, "NONE")

    last_closed = closes[-2]
    current_candle = closes[-1]

    if current_candle > last_closed:
        direction = "UP"
    elif current_candle < last_closed:
        direction = "DOWN"
    else:
        direction = "NONE"

    return (current_candle, direction)

# -------------------- Self-runnable test --------------------
if __name__ == "__main__":
    # Fetch data for TICKER from config
    df = fetch_yf_data()
    price, direction = detect_raw_direction(df)

    # Convert price to integer
    price_int = int(price) if price is not None else "-"

    # Apply color
    if direction == "UP":
        color = Fore.GREEN
    elif direction == "DOWN":
        color = Fore.RED
    else:
        color = Fore.YELLOW

    left_text = f"Price:{price_int}"
    right_text = f"Mullu:{direction}"

    # Color only price and direction
    left_text_colored = color + left_text + Style.RESET_ALL
    right_text_colored = color + right_text + Style.RESET_ALL

    # Calculate spacing for 42-char width
    space_width = TOTAL_WIDTH - len(left_text) - len(right_text)
    if space_width < 0:
        space_width = 1
    spacing = " " * space_width

    # Print final line
    print(left_text_colored + spacing + right_text_colored)
