import pandas as pd

def get_p_series(df):
    c, o, h, l = df['Close'], df['Open'], df['High'], df['Low']
    c1 = c.shift(1)
    e1, e2 = c, (c1 + c) / 2
    e3, e4 = (c + o) / 2, (o + h + l + c) / 4
    return ((e1 + e2 + e3 + e4) / 4).round(4)

def get_bos_bar(df):
    try:
        # Check for minimum data
        if df is None or len(df) < 43:
            return "━" * 42, "0%"

        # 1. P-Master Rolling Logic (42 candles)
        p_vals = get_p_series(df)
        is_up = p_vals > p_vals.shift(1)
        subset = is_up.iloc[-42:]
        
        # 2. Visual Bar Construction (42 characters)
        # Body (Up) = █, Wick (Otherwise) = ━
        visual_bar = "".join(["█" if up else "━" for up in subset])

        # 3. Strength Percentage (Low to Close Comparison)
        latest = df.iloc[-1]
        c, h, l = latest['Close'], latest['High'], latest['Low']
        
        if h != l:
            # Position of Close relative to Low-High range
            strength_val = round(((c - l) / (h - l)) * 100)
        else:
            strength_val = 50
            
        # Clamp strictly between 1 and 99
        strength_pct = f"{max(1, min(99, strength_val))}%"

        # Returns only the visual bar and the percentage
        return visual_bar, strength_pct

    except Exception:
        return "━" * 42, "ERR%"



