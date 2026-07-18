# sysexitpxy.py
import pandas as pd
from syscnfgpxy import PARAMS  # Only TICKER will be used
from sysdtafpxy import fetch_yf_data
from colorama import Fore, Style, init

# Initialize Colorama
init(autoreset=True)

# -------------------- Hardcoded constants --------------------
TOTAL_WIDTH = 42

# -------------------- Direction logic --------------------
def detect_raw_direction(df: pd.DataFrame) -> tuple:
    """
    Returns:
        (latest_price, direction)
    
    Intraday Candle Structural Logic:
    - UP  : Running Close > Current Candle Open
    - DOWN: Running Close < Current Candle Open
    - NONE: Running Close == Current Candle Open or missing data
    """
    if df is None or df.empty:
        return (None, "NONE")

    # Extract the absolute latest candle row from the data feed
    latest_row = df.iloc[-1]

    # Assign core metrics using current candle structural bounds
    current_candle_open = latest_row['Open']
    running_close = latest_row['Close']

    # Evaluate dynamic direction state
    if running_close > current_candle_open:
        direction = "UP"
    elif running_close < current_candle_open:
        direction = "DOWN"
    else:
        direction = "NONE"

    return (running_close, direction)

# -------------------- Self-runnable test --------------------
if __name__ == "__main__":
    # Fetch data for TICKER from config
    df = fetch_yf_data()
    price, direction = detect_raw_direction(df)

    # Convert price to integer safely using rounding logic
    price_int = int(round(price)) if price is not None else "-"

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

