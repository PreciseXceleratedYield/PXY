import pandas as pd
import numpy as np
from sysdthapxy import get_pxy_data

GREEN = "\033[92m"
RED = "\033[91m"
RESET = "\033[0m"

def get_candle_visual(df=None, last_n=100):
    """
    Constructs an upward progressing timeline stream (123...9101112).
    Fixes the 'all 1s' bug by calculating streaks per bar BEFORE splitting digits.
    """
    try:
        output = get_pxy_data(df=df)
    except Exception as e:
        return f"{RED}[Data Source Error: {str(e)[:18]}...]{RESET}"
    
    if output is None:
        return ""
        
    if isinstance(output, tuple):
        # Unpack output safely assuming it matches your original structure: (_, _, pxy_color_series, _)
        pxy_color_series = next((item for item in output if isinstance(item, pd.Series)), None)
    elif isinstance(output, pd.Series):
        pxy_color_series = output
    else:
        pxy_color_series = None

    if pxy_color_series is None or pxy_color_series.empty:
        return ""
        
    # Grab a larger history buffer to calculate streaks accurately from their true origin
    raw_colors = pxy_color_series.iloc[-last_n:]
    
    all_characters = []
    current_streak = 0
    last_color = None
    
    # Pass 1: Calculate streaks purely based on the original data bars
    for color_string in raw_colors:
        if color_string == last_color:
            current_streak += 1
        else:
            current_streak = 1
            last_color = color_string
            
        streak_str = str(current_streak)
        color_code = GREEN if color_string == "green" else RED
        
        # Pass 2: Now safely split the multi-digit numbers into characters
        for char in streak_str:
            all_characters.append({
                'char': char,
                'color': color_code
            })

    # Pass 3: Keep exactly the latest 42 character columns to maintain strict layout size
    latest_characters = all_characters[-42:]
    
    # Build final colorized string stream output
    visual_stream = "".join([f"{item['color']}{item['char']}{RESET}" for item in latest_characters])
    
    return visual_stream

if __name__ == "__main__":
    print("\nCLOSE-MOMENTUM CONFIRMED VISUAL STREAM (Exact 42 Column Width):")
    print(get_candle_visual())
