# sysmktpxy.py
from sysdtafpxy import fetch_yf_data

def get_signal(df=None):
    try:
        if df is None: df = fetch_yf_data()
    except Exception: return "NONE", "NONE"
    
    if df is None or len(df) < 5: return "NONE", "NONE"

    def get_p(i):
        # Master Price smoothing (e1-e4 blend)
        o, h, l, c = df['Open'].iloc[i], df['High'].iloc[i], df['Low'].iloc[i], df['Close'].iloc[i]
        c1 = df['Close'].iloc[i-1]
        e1, e2 = c, (c1 + c) / 2
        e3, e4 = (c + o) / 2, (o + h + l + c) / 4
        return round((e1 + e2 + e3 + e4) / 4, 4)

    try:
        p0, p1, p2, p3 = get_p(-1), get_p(-2), get_p(-3), get_p(-4)
    except: return "NONE", "NONE"

    # --- 1. ENTRY LOGIC (STRICT CONFIRMATION) ---
    # Only acts on closed candles (p1, p2, p3)
    entry = "NONE"
    if p1 > p2 and p3 > p2: entry = "BUY"
    elif p1 < p2 and p3 < p2: entry = "SELL"
    elif p1 > p2: entry = "BULL"
    elif p1 < p2: entry = "BEAR"

    # --- 2. EXIT LOGIC (HYBRID: RAPID + CONFIRMATION) ---
    # Follows confirmation while allowing immediate p0 (running) reaction
    exit_sig = "NONE"
    
    # Early Exit Condition: If live price (p0) flips against the current trend
    is_rapid_buy = p0 > p1 and p2 > p1
    is_rapid_sell = p0 < p1 and p2 < p1
    
    # Confirmation Condition: If last closed trend is already confirmed
    is_confirmed_buy = p1 > p2 and p3 > p2
    is_confirmed_sell = p1 < p2 and p3 < p2

    if is_rapid_buy or is_confirmed_buy:
        exit_sig = "BUY"
    elif is_rapid_sell or is_confirmed_sell:
        exit_sig = "SELL"
    elif p0 > p1:
        exit_sig = "BULL"
    elif p0 < p1:
        exit_sig = "BEAR"

    return entry, exit_sig

if __name__ == "__main__":
    entry, exit_sig = get_signal()
    print(f"ENTRY (Confirmed): {entry}")
    print(f"EXIT (Early/Confirmed): {exit_sig}")



