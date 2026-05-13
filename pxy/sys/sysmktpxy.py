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
    return float(coeffs * (len(y) - 1) + coeffs) 

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

    # Guard gate lowered to 3 to accept your rolling accumulation window
    if df is None or len(df) < 3: 
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
        p_high, p_low = h_s.iloc[-2], l_s.iloc[-2] 
    upper_b = ((p_high + c1) / 2) + (0.25 * atr) 
    lower_b = ((p_low + c1) / 2) - (0.25 * atr) 

    # --- 3. TSMA & MEMORY LOGIC (Last 7 Bars) --- 
    tsma0 = calc_tsma_np(c_s, 7) 
    tsma1 = calc_tsma_np(c_s.iloc[:-1], 7) 

    # Guarded lookback scaling for when history is < 7
    current_lookback = min(7, len(df))
    had_recent_ceiling = (h_s.tail(current_lookback) >= upper_b).any() 
    had_recent_floor = (l_s.tail(current_lookback) <= lower_b).any() 

    if DEBUG: 
        print(f"\n--- PXY DEBUG --- Price: {c0} | TSMA: {tsma0:.2f} | ST: {st0:.2f}") 
        print(f"Locked Boundaries: UP {upper_b:.2f} | LO {lower_b:.2f}") 
        print(f"Memory ({current_lookback}-bar): Ceiling_Touch: {had_recent_ceiling} | Floor_Touch: {had_recent_floor}") 

    # --- 4. ENTRY LOGIC --- 
    entry = "NONE" 
    p_cross_tsma_up = (c1 <= tsma1 and c0 > tsma0) 
    p_cross_tsma_dn = (c1 >= tsma1 and c0 < tsma0) 
    p_cross_black_up = (c1 <= st1 and c0 > st0) 
    p_cross_black_dn = (c1 >= st1 and c0 < st0) 
    above_black, below_black = (c0 > st0), (c0 < st0) 

    if (p_cross_tsma_up and had_recent_floor) or (p_cross_tsma_up and above_black) or p_cross_black_up: 
        entry = "BUY" 
    elif (p_cross_tsma_dn and below_black) or (p_cross_tsma_dn and had_recent_ceiling) or p_cross_black_dn: 
        entry = "SELL" 
    elif above_black and c0 > tsma0: 
        entry = "BULL" 
    elif below_black and c0 < tsma0: 
        entry = "BEAR" 

    # FIX: Morning Safety Filter has been completely removed to prevent blocking signals.
    # Entry conditions pass directly through to execution at all times.

    # --- 5. EXIT LOGIC --- 
    def get_layers(idx): 
        c, o, h, l = df['Close'].iloc[idx], df['Open'].iloc[idx], df['High'].iloc[idx], df['Low'].iloc[idx] 
        c_prev = df['Close'].iloc[idx-1] 
        return round((c + (c_prev+c)/2 + (c+o)/2 + (o+h+l+c)/4) / 4, 4) 

    p0, p1 = get_layers(-1), get_layers(-2) 
    exit_sig = "BUY" if p0 > p1 else "SELL" 
    return entry, exit_sig 

if __name__ == "__main__": 
    e, x = get_signal() 
    print(f"Final Execution -> Entry: {e}, Exit: {x}")





