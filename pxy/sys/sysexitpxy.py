# sysexitpxy.py
import pandas as pd
import numpy as np
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
    
    SuperTrend (1, 1) direction logic engineered to match TradingView.
    Processes full historical data to prevent calculation drift.
    """
    # CRITICAL MATCH FIX: Copy the entire dataframe to preserve full history memory
    df_window = df.copy()

    if len(df_window) < 3:
        latest_price = df['Close'].iloc[-1] if not df.empty else None
        return (latest_price, "NONE")

    # 1. Calculate True Range (TR)
    df_window['H-L'] = df_window['High'] - df_window['Low']
    df_window['H-PC'] = (df_window['High'] - df_window['Close'].shift(1)).abs()
    df_window['L-PC'] = (df_window['Low'] - df_window['Close'].shift(1)).abs()
    df_window['TR'] = df_window[['H-L', 'H-PC', 'L-PC']].max(axis=1)

    # 2. Compute Average True Range (ATR) with Period = 1
    # ATR(1) is identical to the TR row itself, matching Pine's ta.atr(1)
    df_window['ATR'] = df_window['TR']

    # 3. Calculate Basic Bands with Factor = 1
    hl2 = (df_window['High'] + df_window['Low']) / 2
    df_window['Basic_Upper'] = hl2 + (1 * df_window['ATR'])
    df_window['Basic_Lower'] = hl2 - (1 * df_window['ATR'])

    # Drop the first row where shift(1) created a NaN value
    df_window = df_window.dropna(subset=['Basic_Upper', 'Basic_Lower']).copy()
    
    if df_window.empty:
        latest_price = df['Close'].iloc[-1] if not df.empty else None
        return (latest_price, "NONE")

    # 4. Iteratively solve final trailing bands and trend direction
    n = len(df_window)
    final_upper = np.zeros(n)
    final_lower = np.zeros(n)
    trend_dir = np.ones(n)  # 1 for UP, -1 for DOWN

    # Convert to fast NumPy arrays to match positional indexing
    basic_upper = df_window['Basic_Upper'].to_numpy()
    basic_lower = df_window['Basic_Lower'].to_numpy()
    close_prices = df_window['Close'].to_numpy()

    # Seed the very first historical row exactly like TradingView initializes
    final_upper[0] = basic_upper[0]
    final_lower[0] = basic_lower[0]
    trend_dir[0] = 1 if close_prices[0] >= basic_lower[0] else -1

    # Loop through all historical bars to accurately calculate trailing stops
    for i in range(1, n):
        # Calculate Final Upper Band
        if (basic_upper[i] < final_upper[i-1]) or (close_prices[i-1] > final_upper[i-1]):
            final_upper[i] = basic_upper[i]
        else:
            final_upper[i] = final_upper[i-1]

        # Calculate Final Lower Band
        if (basic_lower[i] > final_lower[i-1]) or (close_prices[i-1] < final_lower[i-1]):
            final_lower[i] = basic_lower[i]
        else:
            final_lower[i] = final_lower[i-1]

        # Evaluate trend flips
        if trend_dir[i-1] == 1 and close_prices[i] < final_lower[i]:
            trend_dir[i] = -1
        elif trend_dir[i-1] == -1 and close_prices[i] > final_upper[i]:
            trend_dir[i] = 1
        else:
            trend_dir[i] = trend_dir[i-1]

    # Pull the final calculated values from the very last index row
    latest_dir_value = trend_dir[-1]
    current_candle_price = close_prices[-1]

    if latest_dir_value == 1:
        direction = "UP"
    elif latest_dir_value == -1:
        direction = "DOWN"
    else:
        direction = "NONE"

    return (current_candle_price, direction)

# -------------------- Self-runnable test --------------------
if __name__ == "__main__":
    df = fetch_yf_data()
    price, direction = detect_raw_direction(df)

    price_int = int(round(price)) if price is not None else "-"

    if direction == "UP":
        color = Fore.GREEN
    elif direction == "DOWN":
        color = Fore.RED
    else:
        color = Fore.YELLOW

    left_text = f"Price:{price_int}"
    right_text = f"Mullu:{direction}"

    left_text_colored = color + left_text + Style.RESET_ALL
    right_text_colored = color + right_text + Style.RESET_ALL

    space_width = TOTAL_WIDTH - len(left_text) - len(right_text)
    if space_width < 0:
        space_width = 1
    spacing = " " * space_width

    print(left_text_colored + spacing + right_text_colored)

