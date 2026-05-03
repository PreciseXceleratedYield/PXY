# sysmktpxy.py
from sysdtafpxy import fetch_yf_data

def get_signal(df=None):
    if df is None: df = fetch_yf_data()
    # Need at least 4 bars to look back at c1 safely
    if df is None or len(df) < 4: return "NONE", "NONE"

    def get_master_price(i):
        o = df['Open'].iloc[i]
        h = df['High'].iloc[i]
        l = df['Low'].iloc[i]
        c = df['Close'].iloc[i]
        c1 = df['Close'].iloc[i-1] # Previous Close
        
        e1 = c                    # Pure C
        e2 = (c1 + c) / 2         # C1 + C / 2
        e3 = (c + o) / 2          # C + O / 2
        e4 = (o + h + l + c) / 4  # OHLC / 4
        
        # Average the 4 engines and round to 4 decimals
        return round((e1 + e2 + e3 + e4) / 4, 4)

    p_now  = get_master_price(-1)
    p_prev = get_master_price(-2)
    p_old  = get_master_price(-3)

    # --- SIMPLE LOGIC ---
    if p_now > p_prev:
        # Flip detected: was falling/flat, now rising
        final = "BUY" if p_prev <= p_old else "BULL"
    elif p_now < p_prev:
        # Flip detected: was rising/flat, now falling
        final = "SELL" if p_prev >= p_old else "BEAR"
    else:
        # Price is identical to 4 decimals
        final = "NONE"

    return final, final

if __name__ == "__main__":
    sig, _ = get_signal()
    print(f"SIGNAL: {sig}")
