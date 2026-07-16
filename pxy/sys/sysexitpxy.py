# sysexitpxy.py
import pandas as pd
import numpy as np
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
    
    SuperTrend (1, 1) direction logic:
    - UP: SuperTrend line indicates Bullish trend (1)
    - DOWN: SuperTrend line indicates Bearish trend (-1)
    - NONE: If insufficient data
    """
    window_size = int(ROLLING_WINDOW_MINUTES * ROWS_PER_MINUTE)
    
    # We need a small lookback buffer before the window to properly compute ATR(1)
    # df.tail(window_size + 2) ensures we have prior rows for shifted comparisons
    df_window = df.tail(window_size + 2).copy()

    if len(df_window) < 3:
        # Fallback if there is not enough historical data for calculations
        latest_price = df['Close'].iloc[-1] if not df.empty else None
        return (latest_price, "NONE")

    # 1. Calculate True Range (TR)
    df_window['H-L'] = df_window['High'] - df_window['Low']
    df_window['H-PC'] = (df_window['High'] - df_window['Close'].shift(1)).abs()
    df_window['L-PC'] = (df_window['Low'] - df_window['Close'].shift(1)).abs()
    df_window['TR'] = df_window[['H-L', 'H-PC', 'L-PC']].max(axis=1)

    # 2. Compute Average True Range (ATR) with Period = 1
    df_window['ATR'] = df_window['TR'].rolling(window=1).mean()

    # 3. Calculate Basic Bands with Factor = 1
    hl2 = (df_window['High'] + df_window['Low']) / 2
    df_window['Basic_Upper'] = hl2 + (1 * df_window['ATR'])
    df_window['Basic_Lower'] = hl2 - (1 * df_window['ATR'])

    # 4. Iteratively solve final trailing bands and trend direction
    final_upper = np.zeros(len(df_window))
    final_lower = np.zeros(len(df_window))
    trend_dir = np.ones(len(df_window))  # 1 for UP, -1 for DOWN

    # Seed the initial index row to avoid boundary issues
    final_upper[0] = df_window['Basic_Upper'].iloc[0]
    final_lower[0] = df_window['Basic_Lower'].iloc[0]

    for i in range(1, len(df_window)):
        # Calculate Final Upper Band
        if (df_window['Basic_Upper'].iloc[i] < final_upper[i-1]) or (df_window['Close'].iloc[i-1] > final_upper[i-1]):
            final_upper[i] = df_window['Basic_Upper'].iloc[i]
        else:
            final_upper[i] = final_upper[i-1]

        # Calculate Final Lower Band
        if (df_window['Basic_Lower'].iloc[i] > final_lower[i-1]) or (df_window['Close'].iloc[i-1] < final_lower[i-1]):
            final_lower[i] = df_window['Basic_Lower'].iloc[i]
        else:
            final_lower[i] = final_lower[i-1]

        # Evaluate trend flips against the trailing thresholds
        if trend_dir[i-1] == 1 and df_window['Close'].iloc[i] < final_lower[i]:
            trend_dir[i] = -1
        elif trend_dir[i-1] == -1 and df_window['Close'].iloc[i] > final_upper[i]:
            trend_dir[i] = 1
        else:
            trend_dir[i] = trend_dir[i-1]

    # Map the final continuous trend state to output format
    latest_dir_value = trend_dir[-1]
    current_candle_price = df_window['Close'].iloc[-1]

    if latest_dir_value == 1:
        direction = "UP"
    elif latest_dir_value == -1:
        direction = "DOWN"
    else:
        direction = "NONE"

    return (current_candle_price, direction)

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
