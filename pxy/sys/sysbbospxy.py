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

        # 1. Cumulative OHLC for the 42-minute window
        window = df.iloc[-42:]
        cumulative_open = window.iloc[0]['Open']
        cumulative_close = window.iloc[-1]['Close']
        hh = window['High'].max()
        ll = window['Low'].min()

        # 2. Body vs Wick Logic (Cumulative)
        # If Current Close > 42-min Open = Green Body (█)
        # If Current Close < 42-min Open = Red Wick (▬)
        is_green = cumulative_close >= cumulative_open
        char = "█" if is_green else "▬"
        
        # Returns a solid 42-character block of that state
        visual_bar = char * 42

        # 3. 1 to 99% Strength (Low to Close comparison over the 42-min range)
        if hh != ll:
            # Where is the current price relative to the 42-min Low and High?
            raw_val = round(((cumulative_close - ll) / (hh - ll)) * 100)
        else:
            raw_val = 50
            
        strength_pct = f"{max(1, min(99, raw_val))}%"

        return visual_bar, strength_pct

    except Exception:
        return "▬" * 42, "ERR%"




