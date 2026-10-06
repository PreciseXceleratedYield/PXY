# syspwerpxy.py
import math
import pandas as pd
from sysdtafpxy import fetch_yf_data
from syscnfgpxy import SYSPWERPXY_LOOKBACK_PERIOD
from colorama import Fore, Style, init

# Initialize Colorama
init(autoreset=True)

# -------------------- Hardcoded constants --------------------
TOTAL_WIDTH = 42

# -------------------- CE/PE Power Calculation --------------------
def get_ce_pe_power(df=None):
    if df is None:
        df = fetch_yf_data(period="2d", interval="1m")
        
    """
    Calculate CE/PE power against the average move over the configured
    closed-candle lookback window.
    Returns:
        direction (str): 'Up', 'Down', 'Flat'
        CEPower (int): 1-9
        PEPower (int): 1-9
    """
    # Fetch data: fallback if insufficient rows (Need at least 5 rows for 3 closed moves + 1 running)
    if df is None or df.empty or len(df) < 5:
        df = fetch_yf_data(period="2d", interval="1m")
    if df.empty or len(df) < 5:
        df = fetch_yf_data(period="5d", interval="1m")
    if df.empty or len(df) < 5:
        return "Flat", 1, 1  # fallback

    df = df[['Close']].astype(float).copy()

    # 1. Calculate absolute candle price changes (Close to Close)
    df['move'] = df['Close'] - df['Close'].shift(1)
    df['abs_move'] = df['move'].abs()

    # 2. Average closed-candle absolute moves, excluding the current running one.
    avg_closed_move_3 = df['abs_move'].shift(1).rolling(
        window=SYSPWERPXY_LOOKBACK_PERIOD, min_periods=1
    ).mean()

    # 3. Track the current running candle's net move
    last_move = float(df['move'].iloc[-1])
    
    # 4. Compute the raw ratio against the closed baseline
    current_baseline = avg_closed_move_3.iloc[-1]
    raw_power = abs(last_move / current_baseline) if current_baseline > 0 else 0

    # 5. Step Scale logic (1.00 or less = 1 | 1.01 to 1.99 = 2 | 2.00 to 2.99 = 3 etc.)
    if raw_power <= 1.0:
        scaled_power = 1
    else:
        scaled_power = math.ceil(raw_power)
        scaled_power = min(scaled_power, 9)  # Cap maximum power at 9

    # Determine direction and assign powers
    if last_move > 0:
        direction = "Up"
        CEPower = scaled_power
        PEPower = 1
    elif last_move < 0:
        direction = "Down"
        CEPower = 1
        PEPower = scaled_power
    else:
        direction = "Flat"
        CEPower = 1
        PEPower = 1

    return direction, CEPower, PEPower

# -------------------- Self-runnable test --------------------
if __name__ == "__main__":
    direction, CEPower, PEPower = get_ce_pe_power()

    # Color coding
    ce_color = Fore.YELLOW if CEPower > 1 else Fore.WHITE
    pe_color = Fore.YELLOW if PEPower > 1 else Fore.WHITE

    # Labels and values
    left_text = f"CE Power:{CEPower}"
    right_text = f"PE Power:{PEPower}"

    left_text_colored = "CE Power:" + ce_color + str(CEPower) + Style.RESET_ALL
    right_text_colored = "PE Power:" + pe_color + str(PEPower) + Style.RESET_ALL

    # Compute spacing for total width = 42
    space_width = TOTAL_WIDTH - len(left_text) - len(right_text)
    if space_width < 0:
        space_width = 1
    spacing = " " * space_width

    # Print single line
    print(left_text_colored + spacing + right_text_colored)
