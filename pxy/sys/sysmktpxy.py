# sysmktpxy.py
import numpy as np
import pandas as pd
from sysdtafpxy import fetch_yf_data
from sysstrndpxy import calculate_supertrend
from syskatrpxy import calculate_atr, calculate_dynamic_k

DEBUG = True 

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
    except Exception as e:
        if DEBUG: print(f"DEBUG: Fetch Error: {e}")
        return "NONE", "NONE"

    if df is None or len(df) < 50: 
        return "NONE", "NONE"

    # --- 1. INDICATORS ---
    df_st = calculate_supertrend(df)
    st0, st1 = df_st['ST'].iloc[-1], df_st['ST'].iloc[-2]
    h_s, l_s, c_s = df['High'], df['Low'], df['Close']
    atr = float(calculate_atr(df).iloc[-1])
    
    c0, c1 = float(c_s.iloc[-1]), float(c_s.iloc[-2])
    h0, l0 = float(h_s.iloc[-1]), float(l_s.iloc[-1])

    # --- 2. LOCKED BOUNDARIES (Shifted 1) ---
    current_date = df.index[-1].date()
    today_df = df[df.index.date == current_date]
    prev_day_df = today_df.iloc[:-1]
    
    if not prev_day_df.empty:
        p_high, p_low = prev_day_df['High'].max(), prev_day_df['Low'].min()
    else:
        # Fallback to previous bar's overall H/L if today_df is just 1 bar
        p_high, p_low = h_s.iloc[-2], l_s.iloc[-2]

    upper_b = ((p_high + c1) / 2) + (0.25 * atr)
    lower_b = ((p_low + c1) / 2) - (0.25 * atr)

    # --- 3. TSMA & MEMORY LOGIC (Last 7 Bars) ---
    tsma0 = calc_tsma_np(c_s, 7)
    tsma1 = calc_tsma_np(c_s.iloc[:-1], 7)
    
    # MEMORY: Did we touch boundaries in ANY of the last 7 bars?
    had_recent_ceiling = (h_s.tail(7) >= upper_b).any()
    had_recent_floor = (l_s.tail(7) <= lower_b).any()

    if DEBUG:
        print(f"\n--- PXY DEBUG --- Price: {c0} | TSMA: {tsma0:.2f} | ST: {st0:.2f}")
        print(f"Locked Boundaries: UP {upper_b:.2f} | LO {lower_b:.2f}")
        print(f"Memory (7-bar): Ceiling_Touch: {had_recent_ceiling} | Floor_Touch: {had_recent_floor}")

    # --- 4. ENTRY LOGIC ---
    entry = "NONE"
    p_cross_tsma_up = (c1 <= tsma1 and c0 > tsma0)
    p_cross_tsma_dn = (c1 >= tsma1 and c0 < tsma0)
    p_cross_black_up = (c1 <= st1 and c0 > st0)
    p_cross_black_dn = (c1 >= st1 and c0 < st0)
    above_black, below_black = (c0 > st0), (c0 < st0)

    # REVISED RULES: Confirmation required for boundaries
    # BUY if: (TSMA Flip + Floor Touch) OR (Trend Breakout) OR (ST Reversal)
    if (p_cross_tsma_up and had_recent_floor) or (p_cross_tsma_up and above_black) or p_cross_black_up:
        entry = "BUY"
    # SELL if: (TSMA Flip + Ceiling Touch) OR (Trend Breakout) OR (ST Reversal)
    elif (p_cross_tsma_dn and below_black) or (p_cross_tsma_dn and had_recent_ceiling) or p_cross_black_dn:
        entry = "SELL"
    elif above_black and c0 > tsma0: 
        entry = "BULL"
    elif below_black and c0 < tsma0: 
        entry = "BEAR"

    # Morning Safety Filter
    if entry in ["BUY", "SELL"] and len(df) < 14: 
        if DEBUG: print("DEBUG: Signal blocked - Morning warm-up (<14 bars)")
        entry = "NONE"

    # --- 5. EXIT LOGIC ---
    def get_layers(idx):
        c, o, h, l = df['Close'].iloc[idx], df['Open'].iloc[idx], df['High'].iloc[idx], df['Low'].iloc[idx]
        c_prev = df['Close'].iloc[idx-1]
        # P-Master calculation
        return round((c + (c_prev+c)/2 + (c+o)/2 + (o+h+l+c)/4) / 4, 4)
    
    p0, p1 = get_layers(-1), get_layers(-2)
    exit_sig = "BUY" if p0 > p1 else "SELL"

    return entry, exit_sig

if __name__ == "__main__":
    e, x = get_signal()
    print(f"Final Execution -> Entry: {e}, Exit: {x}")



