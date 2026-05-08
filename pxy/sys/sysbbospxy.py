import pandas as pd

def get_p_series(df):
    c, o, h, l = df['Close'], df['Open'], df['High'], df['Low']
    c1 = c.shift(1)
    e1, e2 = c, (c1 + c) / 2
    e3, e4 = (c + o) / 2, (o + h + l + c) / 4
    return ((e1 + e2 + e3 + e4) / 4).round(4)

def get_bos_bar(df):
    try:
        # Check if we have at least 42 periods for the rolling window
        if df is None or len(df) < 43:
            return "━" * 42, "0%"

        # 1. 42-Minute Rolling Window (Each char is 1 candle)
        p_vals = get_p_series(df)
        is_up = p_vals > p_vals.shift(1)
        subset = is_up.iloc[-42:] # Last 42 candles
        
        # █ for bodies (up), ━ for wicks (down)
        visual_bar = "".join(["█" if up else "━" for up in subset])

        # 2. Low to Close Comparison (Present Candle)
        latest = df.iloc[-1]
        cur_c, hh, ll = latest['Close'], latest['High'], latest['Low']
        
        if hh != ll:
            # How close is the present price to the bottom (LL)?
            raw_val = round(((cur_c - ll) / (hh - ll)) * 100)
        else:
            raw_val = 50 # Neutral if no movement
            
        # Strictly clamp 1 to 99
        strength_pct = f"{max(1, min(99, raw_val))}%"

        return visual_bar, strength_pct

    except Exception:
        return "━" * 42, "ERR%"



