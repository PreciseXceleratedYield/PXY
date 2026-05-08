import pandas as pd

def get_p_series(df):
    c, o, h, l = df['Close'], df['Open'], df['High'], df['Low']
    c1 = c.shift(1)
    e1, e2 = c, (c1 + c) / 2
    e3, e4 = (c + o) / 2, (o + h + l + c) / 4
    return ((e1 + e2 + e3 + e4) / 4).round(4)

def get_bos_bar(df):
    try:
        if df is None or len(df) < 42:
            return "▬" * 42, "0%"

        # 1. 42-Minute Cumulative Range
        window = df.iloc[-42:]
        hh, ll = window['High'].max(), window['Low'].min()
        curr_c = df.iloc[-1]['Close']
        
        # 2. Momentum Check
        p_vals = get_p_series(df)
        is_up = p_vals.iloc[-1] > p_vals.iloc[-2]
        
        # 3. ANSI Escape Codes for real color depth
        # \033[38;5;255m = Pure White
        # \033[38;5;242m = Distinct Medium-Dark Grey
        # \033[0m = Reset
        if is_up:
            visual_bar = "\033[38;5;255m" + "█" * 42 + "\033[0m"
        else:
            visual_bar = "\033[38;5;242m" + "▬" * 42 + "\033[0m"

        # 4. Strength % (1-99%)
        if hh != ll:
            raw_val = round(((curr_c - ll) / (hh - ll)) * 100)
            strength_pct = f"{max(1, min(99, raw_val))}%"
        else:
            strength_pct = "50%"

        return visual_bar, strength_pct

    except Exception:
        return "\033[38;5;242m" + "▬" * 42 + "\033[0m", "ERR%"




