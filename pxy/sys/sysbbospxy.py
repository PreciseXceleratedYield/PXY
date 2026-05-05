from colorama import Fore, Style, init
import pandas as pd

init(autoreset=True)

# ANSI for the visual stream
GREEN_C = "\033[92m"
RED_C   = "\033[91m"
RESET   = "\033[0m"

def get_p_series(df):
    c, o, h, l = df['Close'], df['Open'], df['High'], df['Low']
    c1 = c.shift(1)
    e1, e2 = c, (c1 + c) / 2
    e3, e4 = (c + o) / 2, (o + h + l + c) / 4
    return ((e1 + e2 + e3 + e4) / 4).round(4)

def get_candle_visual_and_counts(df, last_n=42):
    p_vals = get_p_series(df)
    is_up = p_vals > p_vals.shift(1)
    subset = is_up.iloc[-last_n:]
    
    # 1. Build the visual string
    visual = "".join([f"{GREEN_C}/{RESET}" if val else f"{RED_C}\{RESET}" for val in subset])
    
    # 2. Extract counts for BOS
    g_count = subset.sum() # True = 1
    r_count = len(subset) - g_count
    
    return visual, g_count, r_count

def get_bos_bar(df):
    visual, g, r = get_candle_visual_and_counts(df, 42)
    
    # Decide BOS
    if g > r:
        signal, color = "BULL", Fore.GREEN
    elif r > g:
        signal, color = "BEAR", Fore.RED
    else:
        signal, color = "SIDE", Fore.LIGHTBLACK_EX
        
    banner = f" ﮩ٨ﮩ٨ـﮩ٨ـﮩﮩ٨ﮩ_{signal}_٨ـﮩ٨ـ٨ﮩ٨ـﮩﮩﮩﮩ"
    return color + banner + Style.RESET_ALL, signal, visual

if __name__ == "__main__":
    # Test
    # banner, sig, vis = get_bos_bar(df)
    pass
