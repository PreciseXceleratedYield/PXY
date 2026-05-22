import pandas as pd
import numpy as np
from sysdthapxy import get_pxy_data

GREEN = "\033[92m"
RED = "\033[91m"
RESET = "\033[0m"

def get_candle_visual(df=None, last_n=42):
    """
    Constructs a clean 1-character-per-bar timeline stream.
    Sanitizes raw string inputs to prevent broken streak resets.
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
        
    # Take the exact last 42 bars to fill your window
    raw_colors = pxy_color_series.iloc[-last_n:]
    
    visual_elements = []
    current_streak = 0
    last_color = None
    
    for raw_string in raw_colors:
        # CRITICAL FIX: Strip invisible spaces/newlines and convert text to lowercase
        if not isinstance(raw_string, str):
            color_string = str(raw_string).strip().lower()
        else:
            color_string = raw_string.strip().lower()
            
        # Compute the cleaned streak progression safely
        if color_string == last_color:
            current_streak += 1
        else:
            current_streak = 1
            last_color = color_string
            
        # If the streak goes beyond 9, cap it and repeat 9
        display_num = 9 if current_streak > 9 else current_streak
        
        # Match against our sanitized string keys
        color_code = GREEN if "green" in color_string else RED
        visual_elements.append(f"{color_code}{display_num}{RESET}")

    return "".join(visual_elements)

if __name__ == "__main__":
    print("\nCLOSE-MOMENTUM CONFIRMED VISUAL STREAM (Sanitized 42 Columns):")
    print(get_candle_visual(last_n=42))

