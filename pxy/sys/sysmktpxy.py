# sysmktpxy.py
from sysdtafpxy import fetch_yf_data

def get_signal(df=None):
    # --- DATA FETCH ---
    try:
        if df is None:
            df = fetch_yf_data()
    except Exception:
        return "NONE", "NONE"

    if df is None or len(df) < 5:
        return "NONE", "NONE"

    # 1. Master Price Calculation
    def get_p(i):
        # i=-1 is the latest candle (running if live)
        o, h, l, c = df['Open'].iloc[i], df['High'].iloc[i], df['Low'].iloc[i], df['Close'].iloc[i]
        c1 = df['Close'].iloc[i-1]
        e1, e2 = c, (c1 + c) / 2
        e3, e4 = (c + o) / 2, (o + h + l + c) / 4
        return round((e1 + e2 + e3 + e4) / 4, 4)

    try:
        # p0 = Running (Live)
        # p1 = Last Closed
        # p2 = Previous Closed
        # p3 = Oldest Closed
        p0, p1, p2, p3 = get_p(-1), get_p(-2), get_p(-3), get_p(-4)
    except:
        return "NONE", "NONE"

    # --- 2. ENTRY LOGIC (Confirmed - Closed Candles Only) ---
    # Using p1, p2, p3 ensures signal won't disappear
    entry = "NONE"
    if p1 > p2 and p3 > p2:
        entry = "BUY"
    elif p1 < p2 and p3 < p2:
        entry = "SELL"
    elif p1 > p2:
        entry = "BULL"
    elif p1 < p2:
        entry = "BEAR"

    # --- 3. EXIT LOGIC (Running - Includes Live Candle p0) ---
    # Immediate reaction based on live price
    exit_sig = "NONE"
    if p0 > p1 and p2 > p1:
        exit_sig = "BUY"
    elif p0 < p1 and p2 < p1:
        exit_sig = "SELL"
    elif p0 > p1:
        exit_sig = "BULL"
    elif p0 < p1:
        exit_sig = "BEAR"

    return entry, exit_sig

if __name__ == "__main__":
    # entry uses closed data; exit_sig uses running data
    entry, exit_sig = get_signal()
    print(f"ENTRY (Confirmed): {entry}")
    print(f"EXIT (Running):   {exit_sig}")


