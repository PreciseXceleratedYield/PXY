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
    try:
        if df is None or len(df) < 43:
            return Fore.LIGHTBLACK_EX + " ﮩ٨ﮩ_WAIT_ﮩ٨ﮩ" + Style.RESET_ALL, "SIDE"

        # 1. P-Master Logic (42 candles)
        p_vals = get_p_series(df)
        is_up = p_vals > p_vals.shift(1)
        subset = is_up.iloc[-42:]
        
        g_count = int(subset.sum())
        r_count = int(len(subset) - g_count)
        
        # 2. Dominant Percentage Calculation
        if g_count >= r_count:
            signal, color = "BULL", Fore.GREEN
            strength_pct = round((g_count / 42) * 100)
        else:
            signal, color = "BEAR", Fore.RED
            strength_pct = round((r_count / 42) * 100)
            
        # 3. Final Banner Format: Only shows the relevant %
        # Example: ﮩ٨ﮩ٨ـﮩ٨ـﮩﮩ٨ﮩ_ 76% BULL _٨ـﮩ٨ـ٨ﮩ٨ـﮩﮩﮩﮩ
        banner = f"     {color}ﮩ٨ﮩ٨ـﮩ٨ـﮩﮩ٨ﮩ_{strength_pct}% {signal}_٨ـﮩ٨ـ٨ﮩ٨ـﮩﮩﮩﮩ{Style.RESET_ALL}"
        
        return banner, signal

    except Exception:
        return Fore.LIGHTBLACK_EX + " ﮩ٨ﮩ_ERR_ﮩ٨ﮩ" + Style.RESET_ALL, "SIDE"



