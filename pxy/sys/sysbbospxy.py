from colorama import Fore, Style, init
import pandas as pd

init(autoreset=True)

def get_p_series(df):
    c, o, h, l = df['Close'], df['Open'], df['High'], df['Low']
    c1 = c.shift(1)
    e1, e2 = c, (c1 + c) / 2
    e3, e4 = (c + o) / 2, (o + h + l + c) / 4
    return ((e1 + e2 + e3 + e4) / 4).round(4)

def get_bos_bar(df):
    """
    Returns exactly TWO values: 
    1. Formatted Heartbeat Banner
    2. Signal String
    """
    try:
        if df is None or len(df) < 43:
            return Fore.LIGHTBLACK_EX + " ﮩ٨ﮩ_WAIT_ﮩ٨ﮩ" + Style.RESET_ALL, "SIDE"

        # 1. P-Master Direction Logic
        p_vals = get_p_series(df)
        is_up = p_vals > p_vals.shift(1)
        subset = is_up.iloc[-42:]
        
        g = subset.sum()
        r = len(subset) - g
        
        # 2. Decide BOS based on 42-candle majority
        if g > r:
            signal, color = "BULL", Fore.GREEN
        elif r > g:
            signal, color = "BEAR", Fore.RED
        else:
            signal, color = "SIDE", Fore.LIGHTBLACK_EX
            
        # 3. Create the clean banner (No visual stream)
        banner = f"{color} ﮩ٨ﮩ٨ـﮩ٨ـﮩﮩ٨ﮩ_{signal}_٨ـﮩ٨ـ٨ﮩ٨ـﮩﮩﮩﮩ{Style.RESET_ALL}"
        
        return banner, signal

    except Exception:
        return Fore.LIGHTBLACK_EX + " ﮩ٨ﮩ_ERR_ﮩ٨ﮩ" + Style.RESET_ALL, "SIDE"


