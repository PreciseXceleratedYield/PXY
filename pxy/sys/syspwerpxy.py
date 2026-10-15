#!/usr/bin/env python3
# syspwerpxy.py
import sys
from pathlib import Path

# ----------------- PATH FIX (MUST BE AT ABSOLUTE TOP) -----------------
HERE = Path(__file__).resolve().parent          # /home/pxy/PXY/pxy/sys
PXY_DIR = HERE.parent                            # /home/pxy/PXY/pxy

# Inject search paths so script can load its neighboring sibling modules
for path in (HERE, PXY_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import math
import pandas as pd
from sysdtafpxy import fetch_yf_data
from colorama import Fore, Style, init

# Initialize Colorama for terminal formatting
init(autoreset=True)

# -------------------- Hardcoded constants --------------------
TOTAL_WIDTH = 42
POWER_LOOKBACK_PERIOD = 14

# -------------------- CE/PE Power Calculation --------------------
def get_ce_pe_power(df=None):
    """
    Calculate power based on the 14-period average candle range (High - Low).
    
    Progression:
      - Ratio <= 1.0: Power is 1 (Less than or equal to average baseline)
      - Ratio > 1.0 : Power scales dynamically into 2, 3, 4, 5... based on actual ratio.
    """
    # Fetch data: fallbacks if insufficient rows (Need 14 closed + 1 running)
    if df is None or df.empty or len(df) < (POWER_LOOKBACK_PERIOD + 1):
        df = fetch_yf_data(period="2d", interval="1m")
    if df.empty or len(df) < (POWER_LOOKBACK_PERIOD + 1):
        df = fetch_yf_data(period="5d", interval="1m")
    if df.empty or len(df) < (POWER_LOOKBACK_PERIOD + 1):
        return "Flat", 1, 1  # Fixed fallback to return pure integer 1 instead of 10

    df = df[['High', 'Low', 'Close']].astype(float).copy()

    # 1. Calculate the point range (High - Low) for each candle
    df['candle_points'] = df['High'] - df['Low']

    # 2. Average of the last 14 closed candles (Excludes current candle using shift)
    avg_closed_range_14 = df['candle_points'].shift(1).rolling(
        window=POWER_LOOKBACK_PERIOD
    ).mean()

    # 3. Track the current running candle's total High - Low range points
    current_candle_range = float(df['High'].iloc[-1] - df['Low'].iloc[-1])
    
    # 4. Extract the historical baseline benchmark value
    current_baseline = avg_closed_range_14.iloc[-1]

    # 5. Pure Percentage-Scale Matrix
    if current_baseline > 0:
        actual_ratio = current_candle_range / current_baseline
        
        if actual_ratio <= 1.0:
            scaled_power = 1                      # Less than or equal to average baseline
        else:
            scaled_power = math.ceil(actual_ratio) # More than average -> rounds up straight into 2, 3, 4...
            scaled_power = min(scaled_power, 9)    # Cap maximum power at 9
    else:
        scaled_power = 1

    # Keep track of directional sign for the return layout mapping
    last_move = float(df['Close'].iloc[-1] - df['Close'].iloc[-2])

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

