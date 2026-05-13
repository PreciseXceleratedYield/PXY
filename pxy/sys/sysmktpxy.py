# sysmktpxy.py 
import numpy as np 
import pandas as pd 
import json 
import os 
from datetime import datetime 
from sysdtafpxy import fetch_yf_data 
from sysstrndpxy import calculate_supertrend 
from syskatrpxy import calculate_atr 

DEBUG = True 

def calc_tsma_np(series, window=7): 
    """Pure NumPy Linear Regression Matching Pine Script's ta.linreg""" 
    if len(series) < window: window = len(series) 
    y = series.tail(window).values 
    x = np.arange(len(y)) 
    coeffs = np.polyfit(x, y, 1) 
    return float(coeffs * (len(y) - 1) + coeffs) 

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

    if df is None or len(df) < 50: return "NONE", "NONE" 
    
    df_calc = df.copy() 
    if df_calc.index.tz is None: 
        df_calc.index = df_calc.index.tz_localize('UTC').tz_convert('Asia/Kolkata') 
    elif str(df_calc.index.tz) != 'Asia/Kolkata': 
        df_calc.index = df_calc.index.tz_convert('Asia/Kolkata')

    # --- 1. DATA ENTRY & ATR SNAPSHOT --- 
    h_s, l_s, c_s, o_s = df_calc['High'], df_calc['Low'], df_calc['Close'], df_calc['Open'] 
    
    # Pine Script: atr_sma = ta.sma(ta.tr, 14)
    prev_close = c_s.shift(1)
    tr = pd.concat([h_s - l_s, (h_s - prev_close).abs(), (l_s - prev_close).abs()], axis=1).max(axis=1)
    atr_series = tr.rolling(14).mean().fillna(20.0)

    # --- 2. Pine Script INTRADAY SESSION COUNTER & ANCHOR BLACK LINE MATH --- 
    df_calc['date_only'] = df_calc.index.date
    df_calc['bar_cnt'] = df_calc.groupby('date_only').cumcount() + 1 
    df_calc['session_sum'] = df_calc.groupby('date_only')['Close'].cumsum()
    df_calc['session_mean'] = df_calc['session_sum'] / df_calc['bar_cnt']
    df_calc['sma_50'] = df_calc.groupby('date_only')['Close'].transform(lambda x: x.rolling(window=50, min_periods=1).mean())
    df_calc['python_hybrid'] = (df_calc['session_mean'] + df_calc['sma_50']) / 2 
    
    # Anchor definition logic at 9:15 AM open bar
    first_bars = df_calc.groupby('date_only').first()
    anchor_values = np.where(first_bars['Close'] > first_bars['Open'], first_bars['High'], first_bars['Low'])
    anchor_map = pd.Series(anchor_values, index=first_bars.index)
    df_calc['anchor'] = df_calc['date_only'].map(anchor_map)
    df_calc['blend'] = ((df_calc['bar_cnt'] - 15) / 30.0).clip(0, 1)
    
    df_calc['ST'] = np.where(
        df_calc['bar_cnt'] <= 15, df_calc['anchor'],
        np.where(
            df_calc['bar_cnt'] <= 45,
            (df_calc['anchor'] * (1 - df_calc['blend'])) + (df_calc['python_hybrid'] * df_calc['blend']),
            df_calc['python_hybrid']
        )
    )
    
    # --- 3. INTRADAY HIGH / LOW BOUNDARIES (Shifted 1 Bar Match) --- 
    df_calc['day_high_running'] = df_calc.groupby('date_only')['High'].cummax()
    df_calc['day_low_running'] = df_calc.groupby('date_only')['Low'].cummin()
    
    # Pine Script Shifted variables: day_high, close, atr_offset
    df_calc['day_high_shifted'] = df_calc['day_high_running'].shift(1)
    df_calc['day_low_shifted'] = df_calc['day_low_running'].shift(1)
    df_calc['close_shifted'] = df_calc['Close'].shift(1)
    df_calc['atr_offset_shifted'] = (0.25 * atr_series).shift(1)
    
    df_calc['upper_boundary_series'] = ((df_calc['day_high_shifted'] + df_calc['close_shifted']) / 2) + df_calc['atr_offset_shifted']
    df_calc['lower_boundary_series'] = ((df_calc['day_low_shifted'] + df_calc['close_shifted']) / 2) - df_calc['atr_offset_shifted']
    
    # --- 4. CONTINUOUS TSMA SERIES & STRATEGY SIGNAL EVALUATION --- 
    tsma_list = [calc_tsma_np(c_s.iloc[:i+1], 7) for i in range(len(df_calc))]
    df_calc['tsma_7'] = tsma_list
    
    # 5. ISOLATE TODAY'S SIGNALS CANVAS (Removes older data frames safely)
    today_date = df_calc.index[-1].date()
    df_today = df_calc[df_calc['date_only'] == today_date].copy()
    
    if df_today.empty:
        return "NONE", "NONE"

    df_today['c1'] = df_today['Close'].shift(1)
    df_today['tsma1'] = df_today['tsma_7'].shift(1)
    df_today['st1'] = df_today['ST'].shift(1)
    
    df_today['priceCrossUp'] = (df_today['c1'] <= df_today['tsma1']) & (df_today['Close'] > df_today['tsma_7'])
    df_today['priceCrossDn'] = (df_today['c1'] >= df_today['tsma1']) & (df_today['Close'] < df_today['tsma_7'])
    df_today['crossAboveBlack'] = (df_today['c1'] <= df_today['st1']) & (df_today['Close'] > df_today['ST'])
    df_today['crossBelowBlack'] = (df_today['c1'] >= df_today['st1']) & (df_today['Close'] < df_today['ST'])
    
    df_today['aboveBlack'] = df_today['Close'] > df_today['ST']
    df_today['belowBlack'] = df_today['Close'] < df_today['ST']
    
    # Loop Memory Matrix Emulation matching ta.highest / ta.lowest across 7 bars
    df_today['highest_high_7'] = df_today['High'].rolling(7, min_periods=1).max()
    df_today['lowest_low_7'] = df_today['Low'].rolling(7, min_periods=1).min()
    df_today['hadRecentCeilingTouch'] = df_today['highest_high_7'] >= df_today['upper_boundary_series']
    df_today['hadRecentFloorTouch'] = df_today['lowest_low_7'] <= df_today['lower_boundary_series']
    
    # Pine Script: isSafe = bar_cnt >= 14
    df_today['isSafe'] = df_today['bar_cnt'] >= 14
    
    df_today['isBuy'] = df_today['isSafe'] & (
        (df_today['priceCrossUp'] & df_today['hadRecentFloorTouch']) | 
        (df_today['priceCrossUp'] & df_today['aboveBlack']) | 
        df_today['crossAboveBlack']
    )
    df_today['isSell'] = df_today['isSafe'] & (
        (df_today['priceCrossDn'] & df_today['hadRecentCeilingTouch']) | 
        (df_today['priceCrossDn'] & df_today['belowBlack']) | 
        df_today['crossBelowBlack']
    )
    
    last_row = df_today.iloc[-1]
    c0, tsma0, st0 = float(last_row['Close']), float(last_row['tsma_7']), float(last_row['ST'])
    upper_b, lower_b = float(last_row['upper_boundary_series']), float(last_row['lower_boundary_series'])
    had_recent_ceiling, had_recent_floor = bool(last_row['hadRecentCeilingTouch']), bool(last_row['hadRecentFloorTouch'])
    
    if DEBUG: 
        print(f"\n--- PXY DEBUG (UNSLICED TV PRO) --- Price: {c0} | TSMA: {tsma0:.2f} | ST: {st0:.2f}") 
        print(f"Locked Boundaries: UP {upper_b:.2f} | LO {lower_b:.2f}") 
        print(f"Memory Matrix (7-bar): Ceiling_Touch: {had_recent_ceiling} | Floor_Touch: {had_recent_floor}") 

    entry = "NONE"
    if last_row['isBuy']: entry = "BUY"
    elif last_row['isSell']: entry = "SELL"
    elif last_row['aboveBlack'] and c0 > tsma0: entry = "BULL"
    elif last_row['belowBlack'] and c0 < tsma0: entry = "BEAR"

    # --- 6. EXIT LOGIC --- 
    c_arr, o_arr, h_arr, l_arr = df_today['Close'].values, df_today['Open'].values, df_today['High'].values, df_today['Low'].values
    def get_layers_array(idx):
        c, o, h, l = c_arr[idx], o_arr[idx], h_arr[idx], l_arr[idx]
        c_prev = c_arr[idx-1] if abs(idx-1) <= len(c_arr) else c
        return round((c + (c_prev+c)/2 + (c+o)/2 + (o+h+l+c)/4) / 4, 4)

    p0 = get_layers_array(-1)
    p1 = get_layers_array(-2) if len(df_today) > 1 else p0
    exit_sig = "BUY" if p0 > p1 else "SELL" 
    
    log_sync_state(df_today.index[-1], entry, exit_sig, c0, tsma0, st0, upper_b, lower_b, had_recent_ceiling, had_recent_floor)
    return entry, exit_sig 

if __name__ == "__main__": 
    e, x = get_signal() 
    print(f"Final Synchronized Outputs -> Entry Status: {e} | Exit Trend: {x}")



