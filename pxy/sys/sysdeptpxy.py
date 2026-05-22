import pandas as pd
import numpy as np
from sysdthapxy import get_pxy_data

GREEN = "\033[92m"
RED = "\033[91m"
RESET = "\033[0m"

def get_candle_visual(df=None, last_n=100):
    """
    Constructs an upward progressing timeline stream (1, 2, 3...) based on streaks.
    Guarantees the output is always exactly 42 printable characters, prioritizing the newest data.
    """
    output = get_pxy_data(df=df)
    
    # Handle empty returns or structural variations safely
    if output is None:
        return ""
        
    # Unpack output safely assuming it matches your original structure: (_, _, pxy_color_series, _)
    if isinstance(output, tuple) and len(output) >= 4:
        pxy_color_series = output[2]
    elif isinstance(output, pd.Series):
        pxy_color_series = output
    else:
        return ""

    if pxy_color_series.empty:
        return ""
        
    # Grab a larger history buffer (e.g., last 100 elements) 
    # This ensures we calculate the true current streak even if it started far back
    raw_colors = pxy_color_series.iloc[-last_n:]
    
    all_elements = []
    current_streak = 0
    last_color = None
    
    # First Pass: Chronological order (Oldest -> Newest) to count UPWARD safely
    for color_string in raw_colors:
        if color_string == last_color:
            current_streak += 1
        else:
            current_streak = 1
            last_color = color_string
            
        streak_str = str(current_streak)
        color_code = GREEN if color_string == "green" else RED
        
        # Track each individual digit character with its color and state
        for char in streak_str:
            all_elements.append({
                'char': char,
                'color': color_code
            })

    # Second Pass: Keep only the latest 42 characters to enforce strict terminal constraints
    latest_elements = all_elements[-42:]
    
    # Build final ANSI string
    visual_stream = "".join([f"{item['color']}{item['char']}{RESET}" for item in latest_elements])
    
    return visual_stream

if __name__ == "__main__":
    print("\nCLOSE-MOMENTUM CONFIRMED VISUAL STREAM (Exact 42 Column Upward Streaks):")
    print(get_candle_visual())

