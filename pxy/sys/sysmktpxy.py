# sysmktpxy.py
from sysdtafpxy import fetch_yf_data

def get_signal(df=None):
    try:
        if df is None: df = fetch_yf_data()
    except Exception: return "NONE", "NONE"
    
    if df is None or len(df) < 5: return "NONE", "NONE"

    # Function to extract all 4 internal layers
    def get_layers(i):
        o, h, l, c = df['Open'].iloc[i], df['High'].iloc[i], df['Low'].iloc[i], df['Close'].iloc[i]
        c1 = df['Close'].iloc[i-1]
        e1 = c
        e2 = (c1 + c) / 2
        e3 = (c + o) / 2
        e4 = (o + h + l + c) / 4
        p = round((e1 + e2 + e3 + e4) / 4, 4)
        return p, e1, e2, e3, e4

    try:
        p0, e1_0, e2_0, e3_0, e4_0 = get_layers(-1)
        p1, e1_1, e2_1, e3_1, e4_1 = get_layers(-2)
        p2, e1_2, e2_2, e3_2, e4_2 = get_layers(-3)
        p3, e1_3, e2_3, e3_3, e4_3 = get_layers(-4)
    except: return "NONE", "NONE"

    # --- 1. ENTRY LOGIC (Status Quo) ---
    entry = "NONE"
    if p1 > p2 and p3 > p2: entry = "BUY"
    elif p1 < p2 and p3 < p2: entry = "SELL"
    elif p1 > p2: entry = "BULL"
    elif p1 < p2: entry = "BEAR"

    # --- 2. EXIT LOGIC (Directional Upgrade Only) ---
    exit_sig = "NONE"
    
    # Is there a pivot structure in any internal layer?
    # layer_buy means a V-shape pivot occurred in e1, e2, e3, or e4
    layer_buy = (e1_1 > e1_2 and e1_3 > e1_2) or (e2_1 > e2_2 and e2_3 > e2_2) or \
                (e3_1 > e3_2 and e3_3 > e3_2) or (e4_1 > e4_2 and e4_3 > e4_2)
                
    # layer_sell means an Inverted-V pivot occurred in e1, e2, e3, or e4
    layer_sell = (e1_1 < e1_2 and e1_3 < e1_2) or (e2_1 < e2_2 and e2_3 < e2_2) or \
                 (e3_1 < e3_2 and e3_3 < e3_2) or (e4_1 < e4_2 and e4_3 < e4_2)

    if p0 > p1:
        # Direction is Up: It can be BULL or upgraded to BUY
        exit_sig = "BUY" if layer_buy else "BULL"
    elif p0 < p1:
        # Direction is Down: It can be BEAR or upgraded to SELL
        exit_sig = "SELL" if layer_sell else "BEAR"

    return entry, exit_sig




