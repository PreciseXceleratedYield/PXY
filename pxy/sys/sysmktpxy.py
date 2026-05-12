# sysmktpxy.py
import numpy as np
import pandas as pd
from sysdtafpxy import fetch_yf_data
from sysstrndpxy import calculate_supertrend
from syskatrpxy import calculate_atr, calculate_dynamic_k 

DEBUG = True # Global Debug Toggle

def calc_tsma_np(series, window=7):
    """Pure NumPy Linear Regression (TSMA) - Returns single float prediction"""
    if len(series) < window: 
        window = len(series)
    y = series.tail(window).values
    x = np.arange(len(y))
    coeffs = np.polyfit(x, y, 1)
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
    except Exception as e:
        if DEBUG: print(f"DEBUG: Fetch Error: {e}")
        return "NONE", "NONE"

    if df is None or len(df) < 50:
        if DEBUG: print(f"DEBUG: Data too short ({len(df) if df is not None else 0} rows)")
        return "NONE", "NONE"

    # --- 1. BLACK LINE (ST) & ATR BOUNDARIES ---
    df_st = calculate_supertrend(df)
    st0 = df_st['ST'].iloc[-1] 
    st1 = df_st['ST'].iloc[-2] 
    
    h_s, l_s, c_s = df['High'], df['Low'], df['Close']
    
    atr_series = calculate_atr(df)
    atr = float(atr_series.iloc[-1])

    current_date = df.index[-1].date()
    today_df = df[df.index.date == current_date]
    
    if not today_df.empty:
        day_high = today_df['High'].max()
        day_low = today_df['Low'].min()
    else:
        day_high, day_low = float(h_s.iloc[-1]), float(l_s.iloc[-1])

    c0, c1 = float(c_s.iloc[-1]), float(c_s.iloc[-2])
    h0, l0 = float(h_s.iloc[-1]), float(l_s.iloc[-1])

    upper_b = ((day_high + c0) / 2) + (0.25 * atr)
    lower_b = ((day_low + c0) / 2) - (0.25 * atr)

    # --- 2. TSMA ---
    tsma0 = calc_tsma_np(c_s, 7)
    tsma1 = calc_tsma_np(c_s.iloc[:-1], 7)

    if DEBUG:
        print(f"\n--- DEBUG DATA ---")
        print(f"Price: {c0} | TSMA: {tsma0:.2f} | Supertrend: {st0:.2f}")
        print(f"Boundaries: UP {upper_b:.2f} | LO {lower_b:.2f} | ATR: {atr:.2f}")
        print(f"Condition Checks: Above_Black: {c0 > st0} | Above_TSMA: {c0 > tsma0}")

    # --- 4. ENTRY LOGIC ---
    entry = "NONE"
    p_cross_tsma_up = (c1 <= tsma1 and c0 > tsma0)
    p_cross_tsma_dn = (c1 >= tsma1 and c0 < tsma0)
    p_cross_black_up = (c1 <= st1 and c0 > st0)
    p_cross_black_dn = (c1 >= st1 and c0 < st0)
    
    above_black = (c0 > st0)
    below_black = (c0 < st0)

    if (p_cross_tsma_up and above_black) or (l0 <= lower_b) or p_cross_black_up:
        entry = "BUY"
        if DEBUG: print(f"DEBUG: BUY Triggered (CrossUp: {p_cross_tsma_up}, LoTouch: {l0 <= lower_b}, STCross: {p_cross_black_up})")
    elif (p_cross_tsma_dn and below_black) or (h0 >= upper_b) or p_cross_black_dn:
        entry = "SELL"
        if DEBUG: print(f"DEBUG: SELL Triggered (CrossDn: {p_cross_tsma_dn}, HiTouch: {h0 >= upper_b}, STCross: {p_cross_black_dn})")
    elif (c0 > tsma0) and above_black:
        entry = "BULL"
    elif (c0 < tsma0) and below_black:
        entry = "BEAR"

    if entry in ["BUY", "SELL"] and len(df) < 14:
        if DEBUG: print(f"DEBUG: Entry {entry} BLOCKED (Morning Safety: {len(df)}/14 candles)")
        entry = "NONE"

    # --- 5. EXIT LOGIC (P-MASTER Simplified for Debug) ---
    def get_layers(idx):
        o, h, l, c = df['Open'].iloc[idx], df['High'].iloc[idx], df['Low'].iloc[idx], df['Close'].iloc[idx]
        c_prev = df['Close'].iloc[idx-1]
        p = round((c + (c_prev+c)/2 + (c+o)/2 + (o+h+l+c)/4) / 4, 4)
        return p
    
    p0, p1, p2 = get_layers(-1), get_layers(-2), get_layers(-3)
    exit_sig = "BUY" if p0 > p1 else "SELL" # Simplified placeholder for final check

    return entry, exit_sig

if __name__ == "__main__":
    e, x = get_signal()
    print(f"Final -> Entry: {e}, Exit: {x}")




