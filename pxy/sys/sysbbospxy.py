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

def get_bos_bar(df):
    """
    Returns exactly TWO values to match sysdashpxy.py:
    1. The formatted banner string (including the visual / \ stream)
    2. The signal string (BULL/BEAR/SIDE)
    """
    try:
        if df is None or len(df) < 43:
            return Fore.LIGHTBLACK_EX + " ﮩ٨ﮩ_WAIT_ﮩ٨ﮩ" + Style.RESET_ALL, "SIDE"

        # 1. Logic
        p_vals = get_p_series(df)
        is_up = p_vals > p_vals.shift(1)
        subset = is_up.iloc[-42:]
        
        g = subset.sum()
        r = len(subset) - g
        
        # 2. Visual Stream (Fixed backslash escape sequence)
        visual = "".join([f"{GREEN_C}/{RESET}" if val else f"{RED_C}\\{RESET}" for val in subset])
        
        # 3. Decide BOS
        if g > r:
            signal, color = "BULL", Fore.GREEN
        elif r > g:
            signal, color = "BEAR", Fore.RED
        else:
            signal, color = "SIDE", Fore.LIGHTBLACK_EX
            
        # 4. Combine Banner and Visual into one string for the dashboard
        banner = f" {color}ﮩ٨ﮩ٨ـ_{signal}_٨ـﮩ٨ـ {Style.RESET_ALL} {visual}"
        
        return banner, signal

    except Exception:
        return Fore.LIGHTBLACK_EX + " ﮩ٨ﮩ_ERR_ﮩ٨ﮩ" + Style.RESET_ALL, "SIDE"

