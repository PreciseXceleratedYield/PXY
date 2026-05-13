# sysmktpxy.py 
import numpy as np 
import pandas as pd 
import json 
import os 
from datetime import datetime 
from sysdtafpxy import fetch_yf_data 
from sysstrndpxy import calculate_supertrend 
from syskatrpxy import calculate_atr, calculate_dynamic_k 

DEBUG = True 

def calc_tsma_np(series, window=7): 
    """Pure NumPy Linear Regression (TSMA)""" 
    if len(series) < window: window = len(series) 
    y = series.tail(window).values 
    x = np.arange(len(y)) 
    coeffs = np.polyfit(x, y, 1) 
    return float(coeffs[0] * (len(y) - 1) + coeffs[1]) 

def log_sync_state(timestamp, entry, exit_sig, price, tsma, st, upper, lower, ceiling_touch, floor_touch): 
    try: 
        dir_path = os.path.expanduser("~/pxy") 
        os.makedirs(dir_path, exist_ok=True) 
        file_path = os.path.join(dir_path, "tv_sync_log.json") 
        log_entry = { 
            "Timestamp": str(timestamp), "Price": float(price), "TSMA": round(float(tsma), 2), 
            "ST_Line": round(float(st), 2), "Ceiling_Boundary": round(float(upper), 2), 
            "Floor_Boundary": round(float(lower), 2), "Ceiling_Touch": bool(ceiling_touch), 
            "Floor_Touch": bool(floor_touch), "Signal_Entry": str(entry), "Signal_Exit": str(exit_sig), 
            "Logged_At": datetime.now().strftime("%Y-%m-%d %H:%M:%S") 
        } 
        logs = [] 
        if os.path.exists(file_path): 
            with open(file_path, "r") as f: 
                try: logs = json.load(f) 
                except: logs = [] 
        logs.append(log_entry) 
        with open(file_path, "w") as f: json.dump(logs[-100:], f, indent=4) 
    except: pass 

def get_signal(df=None): 
    try: 
        if df is None: df = fetch_yf_data() 
        if not isinstance(df.index, pd.DatetimeIndex): 
            date_col = next((c for c in ['Datetime', 'Date', 'timestamp', 'time'] if c in df.columns), None) 
            if date_col: 
                df[date_col] = pd.to_datetime(df[date_col]) 
                df.set_index(date_col, inplace=True) 
            else: return "NONE", "NONE" 
    except Exception as e: 
        if DEBUG: print(f"DEBUG: Fetch Error: {e}") 
        return "NONE", "NONE" 

    if df is None or len(df) < 3: return "NONE", "NONE" 
    df_calc = df.copy() 

    # --- 1. INDICATORS --- 
    df_st = calculate_supertrend(df_calc) 
    st0, st1 = df_st['ST'].iloc[-1], df_st['ST'].iloc[-2] 
    h_s, l_s, c_s = df_calc['High'], df_calc['Low'], df_calc['Close'] 
    atr_series = calculate_atr(df_calc) 
    c0, c1 = float(c_s.iloc[-1]), float(c_s.iloc[-2]) 
    h0, l0 = float(h_s.iloc[-1]), float(l_s.iloc[-1]) 

    # --- 2. LOCKED BOUNDARIES (Today's Intraday Only Match) --- 
    # Extract today's actual calendar date from the very last row in the frame
    today_date = df_calc.index[-1].date()
    
    # Initialize separate tracking arrays matching your candle size
    day_highs = np.zeros(len(df_calc))
    day_lows = np.zeros(len(df_calc))
    
    # Track the active high/low baseline initialized at the first bar of the dataset
    curr_high = float(h_s.iloc[0])
    curr_low = float(l_s.iloc[0])
    
    for i in range(len(df_calc)):
        row_date = df_calc.index[i].date()
        
        # FIX: If the row belongs to a past day, it is ignored and resets to that specific bar's values.
        # Once it hits today's date, it locks and calculates cumulative expansion smoothly.
        if row_date != today_date:
            curr_high = float(h_s.iloc[i])
            curr_low = float(l_s.iloc[i])
        else:
            # We are inside today's session -> accumulate high/low metrics actively
            curr_high = max(curr_high, float(h_s.iloc[i]))
            curr_low = min(curr_low, float(l_s.iloc[i]))
            
        day_highs[i] = curr_high
        day_lows[i] = curr_low
        
    df_calc['day_high'] = day_highs
    df_calc['day_low'] = day_lows
    
    # Shift arrays by 1 bar to mimic historical boundary locking
    df_calc['p_high_shifted'] = df_calc['day_high'].shift(1).fillna(df_calc['High']) 
    df_calc['p_low_shifted'] = df_calc['day_low'].shift(1).fillna(df_calc['Low']) 
    df_calc['close_shifted'] = df_calc['Close'].shift(1).fillna(df_calc['Close']) 
    df_calc['atr_offset_shifted'] = (0.25 * atr_series).shift(1).fillna(0.25 * atr_series) 
    
    # Assemble final boundary lines tracking today's price action exclusively
    df_calc['upper_boundary_series'] = ((df_calc['p_high_shifted'] + df_calc['close_shifted']) / 2) + df_calc['atr_offset_shifted'] 
    df_calc['lower_boundary_series'] = ((df_calc['p_low_shifted'] + df_calc['close_shifted']) / 2) - df_calc['atr_offset_shifted'] 
    
    upper_b = float(df_calc['upper_boundary_series'].iloc[-1]) 
    lower_b = float(df_calc['lower_boundary_series'].iloc[-1]) 

    # --- 3. TSMA & MEMORY LOGIC (7-Bar Window Matrix) --- 
    tsma0 = calc_tsma_np(c_s, 7) 
    tsma1 = calc_tsma_np(c_s.iloc[:-1], 7) 
    current_lookback = min(7, len(df_calc)) 
    had_recent_ceiling = (df_calc['High'].tail(current_lookback) >= df_calc['upper_boundary_series'].tail(current_lookback)).any() 
    had_recent_floor = (df_calc['Low'].tail(current_lookback) <= df_calc['lower_boundary_series'].tail(current_lookback)).any() 

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

    if (p_cross_tsma_up and had_recent_floor) or (p_cross_tsma_up and above_black) or p_cross_black_up: entry = "BUY" 
    elif (p_cross_tsma_dn and below_black) or (p_cross_tsma_dn and had_recent_ceiling) or p_cross_black_dn: entry = "SELL" 
    elif above_black and c0 > tsma0: entry = "BULL" 
    elif below_black and c0 < tsma0: entry = "BEAR" 

    # --- 5. EXIT LOGIC --- 
    def get_layers(idx): 
        c, o, h, l = df_calc['Close'].iloc[idx], df_calc['Open'].iloc[idx], df_calc['High'].iloc[idx], df_calc['Low'].iloc[idx] 
        c_prev = df_calc['Close'].iloc[idx-1] 
        return round((c + (c_prev+c)/2 + (c+o)/2 + (o+h+l+c)/4) / 4, 4) 

    p0, p1 = get_layers(-1), get_layers(-2) 
    exit_sig = "BUY" if p0 > p1 else "SELL" 
    log_sync_state(df_calc.index[-1], entry, exit_sig, c0, tsma0, st0, upper_b, lower_b, had_recent_ceiling, had_recent_floor) 
    return entry, exit_sig 

if __name__ == "__main__": 
    e, x = get_signal() 
    print(f"Final Execution -> Entry: {e}, Exit: {x}")



