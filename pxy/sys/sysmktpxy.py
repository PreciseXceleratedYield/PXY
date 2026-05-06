# sysmktpxy.py
from sysdtafpxy import fetch_yf_data

def get_signal(df=None):
    try:
        if df is None: df = fetch_yf_data()
    except Exception: return "NONE", "NONE"
    
    if df is None or len(df) < 5: return "NONE", "NONE"

    def get_layers(i):
        o, h, l, c = df['Open'].iloc[i], df['High'].iloc[i], df['Low'].iloc[i], df['Close'].iloc[i]
        c1 = df['Close'].iloc[i-1]
        e1, e2 = c, (c1 + c) / 2
        e3, e4 = (c + o) / 2, (o + h + l + c) / 4
        p = round((e1 + e2 + e3 + e4) / 4, 4)
        return p, e1, e2, e3, e4

    try:
        # p0 = Running/Live, p1 = Last Closed, p2 = Prev Closed, p3 = Oldest
        p0, e1_0, e2_0, e3_0, e4_0 = get_layers(-1)
        p1, e1_1, e2_1, e3_1, e4_1 = get_layers(-2)
        p2, e1_2, e2_2, e3_2, e4_2 = get_layers(-3)
        p3, e1_3, e2_3, e3_3, e4_3 = get_layers(-4)
    except: return "NONE", "NONE"

    # ==========================================
    # 1. ENTRY LOGIC (Strictly Closed: 1, 2, 3)
    # ==========================================
    entry = "NONE"
    orig_c_buy  = p1 > p2 and p3 > p2
    orig_c_sell = p1 < p2 and p3 < p2
    
    # Layer Check for Entry
    c_l_pivot = (e1_1 > e1_2 and e1_3 > e1_2) or (e2_1 > e2_2 and e2_3 > e2_2) or \
                (e3_1 > e3_2 and e3_3 > e3_2) or (e4_1 > e4_2 and e4_3 > e4_2) or \
                (e1_1 < e1_2 and e1_3 < e1_2) or (e2_1 < e2_2 and e2_3 < e2_2) or \
                (e3_1 < e3_2 and e3_3 < e3_2) or (e4_1 < e4_2 and e4_3 < e4_2)

    if orig_c_buy:
        entry = "BUY"
    elif orig_c_sell:
        entry = "SELL"
    elif p1 > p2:
        entry = "BUY" if c_l_pivot else "BULL"
    elif p1 < p2:
        entry = "SELL" if c_l_pivot else "BEAR"

    # ==========================================
    # 2. EXIT LOGIC (Running/Live: 0, 1, 2)
    # ==========================================
    exit_sig = "NONE"
    orig_r_buy  = p0 > p1 and p2 > p1
    orig_r_sell = p0 < p1 and p2 < p1
    
    # Layer Check for Exit (Using Live Candle p0)
    r_l_pivot = (e1_0 > e1_1 and e1_2 > e1_1) or (e2_0 > e2_1 and e2_2 > e2_1) or \
                (e3_0 > e3_1 and e3_2 > e3_1) or (e4_0 > e4_1 and e4_2 > e4_1) or \
                (e1_0 < e1_1 and e1_2 < e1_1) or (e2_0 < e2_1 and e2_2 < e2_1) or \
                (e3_0 < e3_1 and e3_2 < e3_1) or (e4_0 < e4_1 and e4_2 < e4_1)

    if orig_r_buy:
        exit_sig = "BUY"
    elif orig_r_sell:
        exit_sig = "SELL"
    elif p0 > p1:
        # It's BULL, but upgrade to BUY if any internal layer pivoted
        exit_sig = "BUY" if r_l_pivot else "BULL"
    elif p0 < p1:
        # It's BEAR, but upgrade to SELL if any internal layer pivoted
        exit_sig = "SELL" if r_l_pivot else "BEAR"

    return entry, exit_sig



