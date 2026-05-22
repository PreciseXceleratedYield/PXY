import pandas as pd
import numpy as np
from sysdthapxy import get_pxy_data

GREEN = "\033[92m"
RED = "\033[91m"
RESET = "\033[0m"

def get_candle_visual(df=None, last_n=100):
    """
    Constructs an upward progressing timeline stream (123...9101112).
    Includes defensive try-except blocks to catch inner module JSON decoder crashes.
    """
    try:
        # Wrap the black-box source function in a try-block to trap raw stream/API failures
        output = get_pxy_data(df=df)
    except Exception as e:
        # Return a clean error indicator that fits within your 42-character window
        return f"{RED}[Data Source Error: {str(e)[:18]}...]{RESET}"
    
    if output is None:
        return ""
        
    # Standard source-tuple extraction fallback logic
    if isinstance(output, tuple):
        # Look specifically for the pandas Series inside the returned tuple
        pxy_color_series = next((item for item in output if isinstance(item, pd.Series)), None)
    elif isinstance(output, pd.Series):
        pxy_color_series = output
    else:
        pxy_color_series = None

    if pxy_color_series is None or pxy_color_series.empty:
        return ""
        
    # Grab a larger history buffer to calculate streaks accurately from their true origin
    raw_colors = pxy_color_series.iloc[-last_n:]
    
    all_elements = []
    current_streak = 0
    last_color = None
    
    # Pass 1: Build the chronological progression numbers (Oldest -> Newest)
    for color_string in raw_colors:
        if color_string == last_color:
            current_streak += 1
        else:
            current_streak = 1
            last_color = color_string
            
        streak_str = str(current_streak)
        color_code = GREEN if color_string == "green" else RED
        
        # Split multi-character numbers across separate terminal columns sequentially
        for char in streak_str:
            all_elements.append({
                'char': char,
                'color': color_code
            })

    # Pass 2: Keep exactly the latest 42 character columns to maintain strict layout size
    latest_elements = all_elements[-42:]
    
    # Build final colorized string stream output
    visual_stream = "".join([f"{item['color']}{item['char']}{RESET}" for item in latest_elements])
    
    return visual_stream

if __name__ == "__main__":
    print("\nCLOSE-MOMENTUM CONFIRMED VISUAL STREAM (Exact 42 Column Width):")
    print(get_candle_visual())


