# visual_stream.py
import pandas as pd
import numpy as np
from sysdthapxy import get_pxy_data

GREEN = "\033[92m"
RED = "\033[91m"
RESET = "\033[0m"

def get_candle_visual(df=None, last_n=42):
    """Constructs stylized string visualization streams cleanly from Script 1 outputs."""
    output = get_pxy_data(df=df)
    
    if output is None or output[3].empty:
        return ""
        
    # Unpack verified structural colors from the single source of truth module
    _, _, pxy_color_series, _ = output
    subset_colors = pxy_color_series.iloc[-last_n:]
    
    # Map directional colors directly to terminal strings
    visual = "".join([
        f"{GREEN}/{RESET}" if color_string == "green" else f"{RED}\{RESET}" 
        for color_string in subset_colors
    ])
    
    return visual

if __name__ == "__main__":
    print("\nCLOSE-MOMENTUM CONFIRMED VISUAL STREAM (Last 42 Closed Bars):")
    print(get_candle_visual(last_n=42))

