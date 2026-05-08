import pandas as pd
from colorama import Fore, Style, init

# Initialize colorama
init(autoreset=True)

def get_p_series(df):
    c, o, h, l = df['Close'], df['Open'], df['High'], df['Low']
    c1 = c.shift(1)
    e1, e2 = c, (c1 + c) / 2
    e3, e4 = (c + o) / 2, (o + h + l + c) / 4
    return ((e1 + e2 + e3 + e4) / 4).round(4)

def get_bos_bar(df):
    try:
        if df is None or len(df) < 42:
            return Fore.LIGHTBLACK_EX + "▬" * 42 + Style.RESET_ALL, "0%"

        # 1. 42-Minute Cumulative High/Low
        window = df.iloc[-42:]
        hh = window['High'].max()
        ll = window['Low'].min()
        curr_c = df.iloc[-1]['Close']
        
        # 2. Body vs Wick Logic (P-Master check)
        p_vals = get_p_series(df)
        is_up = p_vals.iloc[-1] > p_vals.iloc[-2]
        
        # 3. Create the Visual Bar with Colors
        if is_up:
            # Solid White Body
            visual_bar = Style.BRIGHT + "█" * 42 + Style.RESET_ALL
        else:
            # Dim Grey Wick (The "Straight Line")
            visual_bar = Style.DIM + Fore.WHITE + "▬" * 42 + Style.RESET_ALL

        # 4. Strength % (Position of current Close within the 42-min HH/LL range)
        if hh != ll:
            raw_val = round(((curr_c - ll) / (hh - ll)) * 100)
        else:
            raw_val = 50
            
        strength_pct = f"{max(1, min(99, raw_val))}%"

        return visual_bar, strength_pct

    except Exception:
        return Style.DIM + "▬" * 42, "ERR%"




