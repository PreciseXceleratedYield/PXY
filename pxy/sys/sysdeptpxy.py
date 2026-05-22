import pandas as pd
import numpy as np
from sysdthapxy import get_pxy_data

GREEN = "\033[92m"
RED = "\033[91m"
RESET = "\033[0m"

def get_candle_visual(df=None, last_n=42):
    """
    Constructs a 1-character-per-bar timeline stream.
    Streaks count up to 9 and repeat '9' until the color breaks.
    """
    try:
        output = get_pxy_data(df=df)
    except Exception as e:
        return f"{RED}[Data Source Error: {str(e)[:18]}...]{RESET}"
    
    if output is None:
        return ""
        
    if isinstance(output, tuple):
        pxy_color_series = next((item for item in output if isinstance(item, pd.Series)), None)
    elif isinstance(output, pd.Series):
        pxy_color_series = output
    else:
        pxy_color_series = None

    if pxy_color_series is None or pxy_color_series.empty:
        return ""
        
    # Since 1 bar always equals 1 character now, we only need the exact last 42 bars
    raw_colors = pxy_color_series.iloc[-last_n:]
    
    visual_elements = []
    current_streak = 0
    last_color = None
    
    for color_string in raw_colors:
        if color_string == last_color:
            current_streak += 1
        else:
            current_streak = 1
            last_color = color_string
            
        # If the streak goes beyond 9, cap it and repeat 9
        display_num = 9 if current_streak > 9 else current_streak
        
        color_code = GREEN if color_string == "green" else RED
        visual_elements.append(f"{color_code}{display_num}{RESET}")

    return "".join(visual_elements)

if __name__ == "__main__":
    print("\nCLOSE-MOMENTUM CONFIRMED VISUAL STREAM (Exact 42 Column Width):")
    print(get_candle_visual(last_n=42))

