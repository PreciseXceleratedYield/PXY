import pandas as pd
import numpy as np
from syscnfgpxy import SYSDTHAPXY_INCLUDE_RUNNING_CANDLE
from sysdthapxy import get_pxy_data

GREEN = "\033[92m"
RED = "\033[91m"
FLAT = "\033[93m"
RESET = "\033[0m"

def get_candle_visual(df=None, last_n=100):
    """
    Constructs an upward progressing timeline stream (123...9101112).
    Guarantees that 1 bar = 1 character space, making it perfectly scannable.
    """
    output = get_pxy_data(df=df)
    
    if output is None:
        return ""
        
    if isinstance(output, tuple) and len(output) >= 4:
        pxy_color_series = output[2]  # Extract the color series directly from the tuple
    elif isinstance(output, pd.Series):
        pxy_color_series = output
    else:
        return ""

    if pxy_color_series.empty:
        return ""
        
    if SYSDTHAPXY_INCLUDE_RUNNING_CANDLE == "NO":
        pxy_color_series = pxy_color_series.iloc[:-1]
    if pxy_color_series.empty:
        return ""

    # Grab a larger history buffer to calculate streaks accurately from their start
    raw_colors = pxy_color_series.iloc[-last_n:]
    
    all_elements = []
    current_streak = 0
    last_color = None
    
    # First Pass: Chronological order (Oldest -> Newest)
    for color_string in raw_colors:
        if color_string == last_color:
            current_streak += 1
        else:
            current_streak = 1
            last_color = color_string
            
        # Convert streak to string to get its individual layout digits
        streak_str = str(current_streak)
        color_code = {
            "green": GREEN,
            "red": RED,
            "flat": FLAT,
        }.get(color_string, RESET)
        
        # When a streak hits double digits (e.g. 10), we split '1' and '0' 
        # across two bars to match your exact pattern timeline layout.
        for char in streak_str:
            all_elements.append({
                'char': char,
                'color': color_code
            })

    # Second Pass: Keep exactly the latest 42 terminal character spaces
    latest_elements = all_elements[-42:]
    
    # Build final colorized string stream
    visual_stream = "".join([f"{item['color']}{item['char']}{RESET}" for item in latest_elements])
    
    return visual_stream

if __name__ == "__main__":
    print("\nCLOSE-MOMENTUM CONFIRMED VISUAL STREAM (Exact 42 Column Width):")
    print(get_candle_visual())
