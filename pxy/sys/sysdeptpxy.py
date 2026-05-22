import pandas as pd
import numpy as np
from sysdthapxy import get_pxy_data

GREEN = "\033[92m"
RED = "\033[91m"
RESET = "\033[0m"

def get_candle_visual(df=None, last_n=42):
    """
    Constructs a 1-character-per-bar timeline stream.
    Maps BULL/GREEN to Green and BEAR/RED to Red with proper streak tracking.
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
    raw_states = pxy_color_series.iloc[-last_n:]
    
    visual_elements = []
    current_streak = 0
    last_state = None
    
    for raw_string in raw_states:
        # Clean the string from hidden spaces and force lowercase
        state_string = str(raw_string).strip().lower()
            
        # Track streak based on matching the current state to the last state
        if state_string == last_state:
            current_streak += 1
        else:
            current_streak = 1
            last_state = state_string
            
        # Cap the streak display at 9
        display_num = 9 if current_streak > 9 else current_streak
        
        # Green for bull trends, Red for bear trends
        if "bull" in state_string or "green" in state_string:
            color_code = GREEN
        else:
            color_code = RED
            
        visual_elements.append(f"{color_code}{display_num}{RESET}")

    return "".join(visual_elements)

if __name__ == "__main__":
    print("\nCLOSE-MOMENTUM CONFIRMED VISUAL STREAM (Exact 42 Column Width):")
    print(get_candle_visual(last_n=42))
