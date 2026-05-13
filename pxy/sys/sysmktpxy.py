# sysmktpxy.py
import numpy as np
import pandas as pd
import json
import os
from datetime import datetime
from sysdtafpxy import fetch_yf_data
from sysstrndpxy import calculate_supertrend  # Uses your upgraded TSMA(50) architecture

DEBUG = True

def calc_tsma_np(series, window=7):
    """Pure NumPy Linear Regression Matching Pine Script's ta.linreg"""
    if len(series) < window:
        window = len(series)
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
            "Timestamp": str(timestamp),
            "Price": float(price),
            "TSMA": round(float(tsma), 2),
            "ST_Line": round(float(st), 2),
            "Ceiling_Boundary": round(float(upper), 2),
            "Floor_Boundary": round(float(lower), 2),
            "Ceiling_Touch": bool(ceiling_touch),
            "Floor_Touch": bool(floor_touch),
            "Signal_Entry": str(entry),
            "Signal_Exit": str(exit_sig),
            "Logged_At": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        logs = []
        if os.path.exists(file_path):
            with open(file_path, "r") as f:
                try:
                    logs = json.load(f)
                except:
                    logs = []
        logs.append(log_entry)
        with open(file_path, "w") as f:
            json.dump(logs[-100:], f, indent=4)
    except:
        pass

def get_signal(df=None):
    if df is None:
        df = fetch_yf_data()
        
    if df is None or df.empty:
        return "NONE", "NONE"
        
    try:
        # --- 1. RUN STRUCTURAL SUPERTREND BACKBONE (REPLACES DUPLICATE LOOPS) ---
        df_calc = calculate_supertrend(df) # Slices to a strict 50-row matrix internally
        
        # --- 2. CALCULATE ATR OVER MATURED DATA VECTOR ---
        h_s, l_s, c_s = df_calc['High'], df_calc['Low'], df_calc['Close']
        prev_close = c_s.shift(1)
        tr = pd.concat([h_s - l_s, (h_s - prev_close).abs(), (l_s - prev_close).abs()], axis=1).max(axis=1)
        atr_series = tr.rolling(14, min_periods=1).mean().fillna(20.0)
        
        # --- 3. DYNAMIC INTRA-MATRIX CHANNELS (REPLACES BROKEN GROUPBY HIGH/LOWS) ---
        df_calc['day_high_running'] = h_s.cummax()
        df_calc['day_low_running'] = l_s.cummax()
        
        df_calc['day_high_shifted'] = df_calc['day_high_running'].shift(1)
        df_calc['day_low_shifted'] = df_calc['day_low_running'].shift(1)
        df_calc['close_shifted'] = c_s.shift(1)
        df_calc['atr_offset_shifted'] = (0.25 * atr_series).shift(1)
        
        df_calc['upper_boundary_series'] = ((df_calc['day_high_shifted'] + df_calc['close_shifted']) / 2) + df_calc['atr_offset_shifted']
        df_calc['lower_boundary_series'] = ((df_calc['day_low_shifted'] + df_calc['close_shifted']) / 2) - df_calc['atr_offset_shifted']
        
        # --- 4. CALC FAST TSMA_7 TRACKER VECTORS ---
        tsma_list = [calc_tsma_np(c_s.iloc[:i+1], 7) if (i >= 1) else float(c_s.iloc[i]) for i in range(len(df_calc))]
        df_calc['tsma_7'] = tsma_list
        
        # --- 5. SIGNAL MATRIX CROSSES ---
        df_calc['c1'] = df_calc['Close'].shift(1)
        df_calc['tsma1'] = df_calc['tsma_7'].shift(1)
        df_calc['st1'] = df_calc['ST'].shift(1)
        
        df_calc['priceCrossUp'] = (df_calc['c1'] <= df_calc['tsma1']) & (df_calc['Close'] > df_calc['tsma_7'])
        df_calc['priceCrossDn'] = (df_calc['c1'] >= df_calc['tsma1']) & (df_calc['Close'] < df_calc['tsma_7'])
        df_calc['crossAboveBlack'] = (df_calc['c1'] <= df_calc['st1']) & (df_calc['Close'] > df_calc['ST'])
        df_calc['crossBelowBlack'] = (df_calc['c1'] >= df_calc['st1']) & (df_calc['Close'] < df_calc['ST'])
        
        df_calc['aboveBlack'] = df_calc['Close'] > df_calc['ST']
        df_calc['belowBlack'] = df_calc['Close'] < df_calc['ST']
        
        df_calc['highest_high_7'] = df_calc['High'].rolling(7, min_periods=1).max()
        df_calc['lowest_low_7'] = df_calc['Low'].rolling(7, min_periods=1).min()
        
        df_calc['hadRecentCeilingTouch'] = df_calc['highest_high_7'] >= df_calc['upper_boundary_series']
        df_calc['hadRecentFloorTouch'] = df_calc['lowest_low_7'] <= df_calc['lower_boundary_series']
        
        # --- 6. ISOLATE ENTRY EXECUTIONS FROM LAST ROW ---
        last_row = df_calc.iloc[-1]
        c0, tsma0, st0 = float(last_row['Close']), float(last_row['tsma_7']), float(last_row['ST'])
        upper_b, lower_b = float(last_row['upper_boundary_series']), float(last_row['lower_boundary_series'])
        had_recent_ceiling, had_recent_floor = bool(last_row['hadRecentCeilingTouch']), bool(last_row['hadRecentFloorTouch'])
        
        if DEBUG:
            print(f"\n--- PXY DEBUG (MATRIC ALIGNED PRO) --- Price: {c0} | TSMA: {tsma0:.2f} | ST: {st0:.2f}")
            print(f"Locked Boundaries: UP {upper_b:.2f} | LO {lower_b:.2f}")
            print(f"Memory Matrix (7-bar): Ceiling_Touch: {had_recent_ceiling} | Floor_Touch: {had_recent_floor}")
            
        entry = "NONE"
        if last_row['bar_cnt'] >= 14:  # Enforces safe buffer check based on the matrix index
            if last_row['isBuy'] := ((last_row['priceCrossUp'] & had_recent_floor) | (last_row['priceCrossUp'] & last_row['aboveBlack']) | last_row['crossAboveBlack']):
                entry = "BUY"
            elif last_row['isSell'] := ((last_row['priceCrossDn'] & had_recent_ceiling) | (last_row['priceCrossDn'] & last_row['belowBlack']) | last_row['crossBelowBlack']):
                entry = "SELL"
            elif last_row['aboveBlack'] and c0 > tsma0:
                entry = "BULL"
            elif last_row['belowBlack'] and c0 < tsma0:
                entry = "BEAR"
                
        # --- 7. EXIT LOGIC LAYER ARRAYS ---
        c_arr, o_arr, h_arr, l_arr = df_calc['Close'].values, df_calc['Open'].values, df_calc['High'].values, df_calc['Low'].values
        
        def get_layers_array(idx):
            c, o, h, l = c_arr[idx], o_arr[idx], h_arr[idx], l_arr[idx]
            c_prev = c_arr[idx-1] if abs(idx-1) <= len(c_arr) else c
            return round((c + (c_prev+c)/2 + (c+o)/2 + (o+h+l+c)/4) / 4, 4)
            
        p0 = get_layers_array(-1)
        p1 = get_layers_array(-2) if len(df_calc) > 1 else p0
        exit_sig = "BUY" if p0 > p1 else "SELL"
        
        log_sync_state(df_calc.index[-1], entry, exit_sig, c0, tsma0, st0, upper_b, lower_b, had_recent_ceiling, had_recent_floor)
        return entry, exit_sig
        
    except Exception as e:
        if DEBUG:
            print(f"PXY Master Core Error: {e}")
        return "NONE", "NONE"

if __name__ == "__main__":
    e, x = get_signal()
    print(f"Final Synchronized Outputs -> Entry Status: {e} | Exit Trend: {x}")

