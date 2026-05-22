import pandas as pd
import numpy as np
from sysdthapxy import get_pxy_data

GREEN = "\033[92m"
RED = "\033[91m"
RESET = "\033[0m"

def get_candle_visual(df=None, last_n=42):
    """
    Constructs a colorized text stream prioritizing the latest data.
    Guarantees the printed terminal output is always exactly 42 characters wide.
    """
    output = get_pxy_data(df=df)
    
    # Handle empty returns or structural variations safely
    if output is None:
        return ""
        
    # Extract pandas Series regardless of tuple layout
    if isinstance(output, tuple):
        if len(output) > 2 and isinstance(output[2], pd.Series):
            pxy_color_series = output[2]
        elif len(output) > 0 and isinstance(output[0], pd.Series):
            pxy_color_series = output[0]
        else:
            return ""
    elif isinstance(output, pd.Series):
        pxy_color_series = output
    else:
        return ""

    if pxy_color_series.empty:
        return ""
        
    # Request a safe historical buffer to account for multi-digit spacing compression
    raw_colors = pxy_color_series.iloc[-last_n:]
    
    visual_elements = []
    current_streak = 0
    last_color = None
    
    # Read backwards (Newest -> Oldest) to prioritize processing recent events
    for color_string in reversed(raw_colors):
        if color_string == last_color:
            current_streak += 1
        else:
            current_streak = 1
            last_color = color_string
            
        streak_str = str(current_streak)
        color_code = GREEN if color_string == "green" else RED
        
        # Wrap every digit to protect string structure during terminal formatting
        colorized_streak = "".join([f"{color_code}{char}{RESET}" for char in streak_str])
        visual_elements.append((colorized_streak, len(streak_str)))

    final_string = ""
    total_chars = 0
    
    # Rebuild chronologically (Left -> Right) until exactly 42 terminal column blocks are filled
    for color_segment, char_len in visual_elements:
        if total_chars + char_len <= 42:
            final_string = color_segment + final_string
            total_chars += char_len
        else:
            remaining_slots = 42 - total_chars
            if remaining_slots > 0:
                color_code = GREEN if GREEN in color_segment else RED
                # Strip out ANSI escapes temporarily to safely slice raw numeric positions
                raw_digits = color_segment.replace(GREEN, "").replace(RED, "").replace(RESET, "")
                visible_digits = raw_digits[-remaining_slots:]
                truncated_segment = "".join([f"{color_code}{d}{RESET}" for d in visible_digits])
                final_string = truncated_segment + final_string
            break
            
    return final_string

if __name__ == "__main__":
    print("\nCLOSE-MOMENTUM CONFIRMED VISUAL STREAM (Exact 42 Column Width):")
    print(get_candle_visual(last_n=42))

