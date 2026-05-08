import pandas as pd

def get_p_series(df):
    c, o, h, l = df['Close'], df['Open'], df['High'], df['Low']
    c1 = c.shift(1)
    e1, e2 = c, (c1 + c) / 2
    e3, e4 = (c + o) / 2, (o + h + l + c) / 4
    return ((e1 + e2 + e3 + e4) / 4).round(4)

def get_bos_bar(df):
    try:
        # Require 42 periods for the cumulative window
        if df is None or len(df) < 42:
            return "▬" * 42, "0%"

        # 1. 42-Minute Cumulative Data
        window = df.iloc[-42:]
        hh = window['High'].max()
        ll = window['Low'].min()
        
        # 2. Determine "Body" vs "Wick" for the 42-min Candle
        # We use the P-series to check if the current momentum is UP
        p_vals = get_p_series(df)
        is_up = p_vals.iloc[-1] > p_vals.iloc[-2]
        
        # If UP (Green Body): █
        # Otherwise (Wick/Straight Line): ▬
        char = "█" if is_up else "▬"
        visual_bar = char * 42

        # 3. 1 to 99% Strength (Low to Close comparison over the 42-min range)
        current_close = df.iloc[-1]['Close']
        if hh != ll:
            # Position of price within the 42-min total range
            raw_val = round(((current_close - ll) / (hh - ll)) * 100)
        else:
            raw_val = 50
            
        strength_pct = f"{max(1, min(99, raw_val))}%"

        return visual_bar, strength_pct

    except Exception:
        return "▬" * 42, "ERR%"





