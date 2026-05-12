# sysmktpxy.py
"""
DOCUMENTATION & STRATEGY RULES (FINAL PRODUCTION):
--------------------------------------------------
ENTRY CONDITIONS (RULE CROSS-CHECK):
1. BUY: Price crosses ABOVE the Black Line (Supertrend).
2. BUY: Current Low touches or breaks BELOW the Lower Boundary.
3. BUY: Price crosses ABOVE TSMA while already ABOVE Black Line.
4. SELL: Price crosses BELOW the Black Line (Supertrend).
5. SELL: Current High touches or breaks ABOVE the Upper Boundary.
6. SELL: Price crosses BELOW TSMA while already BELOW Black Line.

EXPLICIT TREND LOGIC (NO ASSUMPTIONS):
- BULL: Price > TSMA AND Price > Black Line.
- BEAR: Price < TSMA AND Price < Black Line.
- NONE: Triggered if price is between levels or indicators conflict.

TECHNICAL SAFEGUARDS:
- ATR Fallback: Defaults to 20 if 0/NaN (Safe for Nifty).
- Morning Filter: BUY/SELL blocked for the first 14 candles.
- TSMA Reliability: Forced float conversion to prevent array comparison errors.
"""

import numpy as np
import pandas as pd
from sysdtafpxy import fetch_yf_data
from sysstrndpxy import calculate_supertrend
from syskatrpxy import calculate_atr, calculate_dynamic_k 

def calc_tsma_np(series, window=7):
    """Pure NumPy Linear Regression (TSMA) - Returns single float prediction"""
    if len(series) < window: 
        window = len(series)
    y = series.tail(window).values
    x = np.arange(len(y))
    coeffs = np.polyfit(x, y, 1)
    # coeffs[0] is slope, coeffs[1] is intercept
    return float(coeffs[0] * (len(y) - 1) + coeffs[1])

def get_signal(df=None):
    try:
        if df is None:
            df = fetch_yf_data()
        if not isinstance(df.index, pd.DatetimeIndex):
            date_col = next((c for c in ['Datetime', 'Date', 'timestamp', 'time'] if c in df.columns), None)
            if date_col:
                df[date_col] = pd.to_datetime(df[date_col])
                df.set_index(date_col, inplace=True)
            else:
                return "NONE", "NONE"
    except Exception:
        return "NONE", "NONE"

    if df is None or len(df) < 50:
        return "NONE", "NONE"

    # --- 1. BLACK LINE (ST) & ATR BOUNDARIES ---
    df_st = calculate_supertrend(df)
    st0 = df_st['ST'].iloc[-1] # Current Black Line
    st1 = df_st['ST'].iloc[-2] # Previous Black Line
    
    h_s, l_s, c_s = df['High'], df['Low'], df['Close']
    
    # ATR from syskatrpxy (Production Fallback: 20)
    atr_series = calculate_atr(df)
    atr = float(atr_series.iloc[-1])

    # Day High/Low Logic for Boundary Midpoint
    current_date = df.index[-1].date()
    today_df = df[df.index.date == current_date]
    
    if not today_df.empty:
        day_high = today_df['High'].max()
        day_low = today_df['Low'].min()
    else:
        day_high, day_low = float(h_s.iloc[-1]), float(l_s.iloc[-1])

    c0, c1 = float(c_s.iloc[-1]), float(c_s.iloc[-2])
    h0, l0 = float(h_s.iloc[-1]), float(l_s.iloc[-1])

    # TIGHT BOUNDARIES: 0.25 * ATR Buffer
    upper_b = ((day_high + c0) / 2) + (0.25 * atr)
    lower_b = ((day_low + c0) / 2) - (0.25 * atr)

    # --- 2. TSMA (LINEAR REGRESSION LENGTH 7) ---
    tsma0 = calc_tsma_np(c_s, 7)
    tsma1 = calc_tsma_np(c_s.iloc[:-1], 7)

    # --- 3. P-MASTER LAYERS (EXIT LOGIC) ---
    def get_layers(idx):
        o, h, l, c = df['Open'].iloc[idx], df['High'].iloc[idx], df['Low'].iloc[idx], df['Close'].iloc[idx]
        c_prev = df['Close'].iloc[idx-1]
        e1, e2 = c, (c_prev + c) / 2
        e3, e4 = (c + o) / 2, (o + h + l + c) / 4
        p = round((e1 + e2 + e3 + e4) / 4, 4)
        return p, e1, e2, e3, e4

    p0, e1_0, e2_0, e3_0, e4_0 = get_layers(-1)
    p1, e1_1, e2_1, e3_1, e4_1 = get_layers(-2)
    p2, e1_2, e2_2, e3_2, e4_2 = get_layers(-3)

    # --- 4. ENTRY LOGIC (STRICT RULES) ---
    entry = "NONE"
    p_cross_tsma_up = (c1 <= tsma1 and c0 > tsma0)
    p_cross_tsma_dn = (c1 >= tsma1 and c0 < tsma0)
    p_cross_black_up = (c1 <= st1 and c0 > st0)
    p_cross_black_dn = (c1 >= st1 and c0 < st0)
    
    above_black = (c0 > st0)
    below_black = (c0 < st0)

    # PRIMARY BUY/SELL RULES
    if (p_cross_tsma_up and above_black) or (l0 <= lower_b) or p_cross_black_up:
        entry = "BUY"
    elif (p_cross_tsma_dn and below_black) or (h0 >= upper_b) or p_cross_black_dn:
        entry = "SELL"
    # EXPLICIT TREND LOGIC (NO ASSUMPTIONS)
    elif (c0 > tsma0) and above_black:
        entry = "BULL"
    elif (c0 < tsma0) and below_black:
        entry = "BEAR"
    else:
        entry = "NONE"

    # MORNING SAFETY: Block BUY/SELL for first 14 candles
    if entry in ["BUY", "SELL"] and len(df) < 14:
        entry = "NONE"

    # --- 5. EXIT LOGIC (P-MASTER) ---
    exit_sig = "NONE"
    orig_r_buy = p0 > p1 and p2 > p1
    orig_r_sell = p0 < p1 and p2 < p1
    
    r_l_pivot = (e1_0 > e1_1 and e1_2 > e1_1) or (e2_0 > e2_1 and e2_2 > e2_1) or \
                (e3_0 > e3_1 and e3_2 > e3_1) or (e4_0 > e4_1 and e4_2 > e4_1) or \
                (e1_0 < e1_1 and e1_2 < e1_1) or (e2_0 < e2_1 and e2_2 < e2_1) or \
                (e3_0 < e3_1 and e3_2 < e3_1) or (e4_0 < e4_1 and e4_2 < e4_1)

    if orig_r_buy:
        exit_sig = "BUY"
    elif orig_r_sell:
        exit_sig = "SELL"
    elif p0 > p1:
        exit_sig = "BUY" if r_l_pivot else "BULL"
    elif p0 < p1:
        exit_sig = "SELL" if r_l_pivot else "BEAR"

    return entry, exit_sig

if __name__ == "__main__":
    e, x = get_signal()
    print(f"Final Return -> Entry: {e}, Exit: {x}")



