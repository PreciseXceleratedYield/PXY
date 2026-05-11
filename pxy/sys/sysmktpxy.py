# sysmktpxy.py
import numpy as np
import pandas as pd
from sysdtafpxy import fetch_yf_data

def calc_tsma_np(series, window=7):
    """Pure NumPy Linear Regression (TSMA)"""
    if len(series) < window: window = len(series)
    y = series.tail(window).values
    x = np.arange(len(y))
    coeffs = np.polyfit(x, y, 1)
    return coeffs[0] * (len(y) - 1) + coeffs[1]

def get_signal(df=None):
    try:
        if df is None:
            df = fetch_yf_data()
    except Exception:
        return "NONE", "NONE"
    
    if df is None or len(df) < 10:
        return "NONE", "NONE"

    def get_layers(i):
        o, h, l, c = df['Open'].iloc[i], df['High'].iloc[i], df['Low'].iloc[i], df['Close'].iloc[i]
        c1_prev = df['Close'].iloc[i-1]
        e1, e2 = c, (c1_prev + c) / 2
        e3, e4 = (c + o) / 2, (o + h + l + c) / 4
        p = round((e1 + e2 + e3 + e4) / 4, 4)
        return p, e1, e2, e3, e4

    try:
        p0, e1_0, e2_0, e3_0, e4_0 = get_layers(-1)
        p1, e1_1, e2_1, e3_1, e4_1 = get_layers(-2)
        p2, e1_2, e2_2, e3_2, e4_2 = get_layers(-3)
        
        tsma0 = calc_tsma_np(df['Close'], 7)
        tsma1 = calc_tsma_np(df['Close'].iloc[:-1], 7)
        c0, c1 = df['Close'].iloc[-1], df['Close'].iloc[-2]
    except:
        return "NONE", "NONE"

    # --- ENTRY (TSMA ONLY) ---
    entry = "NONE"
    if c1 <= tsma1 and c0 > tsma0: entry = "BUY"
    elif c1 >= tsma1 and c0 < tsma0: entry = "SELL"
    elif c0 > tsma0: entry = "BULL"
    elif c0 < tsma0: entry = "BEAR"

    # --- EXIT (P-MASTER ONLY) ---
    exit_sig = "NONE"
    orig_r_buy = p0 > p1 and p2 > p1
    orig_r_sell = p0 < p1 and p2 < p1
    r_l_pivot = (e1_0 > e1_1 and e1_2 > e1_1) or (e2_0 > e2_1 and e2_2 > e2_1) or \
                (e3_0 > e3_1 and e3_2 > e3_1) or (e4_0 > e4_1 and e4_2 > e4_1) or \
                (e1_0 < e1_1 and e1_2 < e1_1) or (e2_0 < e2_1 and e2_2 < e2_1) or \
                (e3_0 < e3_1 and e3_2 < e3_1) or (e4_0 < e4_1 and e4_2 < e4_1)

    if orig_r_buy: exit_sig = "BUY"
    elif orig_r_sell: exit_sig = "SELL"
    elif p0 > p1: exit_sig = "BUY" if r_l_pivot else "BULL"
    elif p0 < p1: exit_sig = "SELL" if r_l_pivot else "BEAR"

    # The print statement you requested
    #print(f"[SIGNAL] Entry(TSMA): {entry} | Exit(PM): {exit_sig} | C:{c0:.2f}")

    return entry, exit_sig

if __name__ == "__main__":
    # Test block to run directly
    e, x = get_signal()
    print(f"Final Return -> Entry: {e}, Exit: {x}")



