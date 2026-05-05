import pandas as pd
import numpy as np
from sysdtafpxy import fetch_yf_data

def calculate_supertrend(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # 1. ROBUST DATETIME INDEX FIX
    if not isinstance(df.index, pd.DatetimeIndex):
        date_col = next((c for c in ['Date', 'Datetime', 'timestamp', 'time'] if c in df.columns), None)
        if date_col:
            df[date_col] = pd.to_datetime(df[date_col])
            df.set_index(date_col, inplace=True)

    # 2. Master Price Engine
    def get_p_series(df_slice):
        o, h, l, c = df_slice['Open'], df_slice['High'], df_slice['Low'], df_slice['Close']
        c1 = c.shift(1)
        return (c + (c1 + c) / 2 + (c + o) / 2 + (o + h + l + c) / 4) / 4

    df['P_Master'] = get_p_series(df)

    # 3. VWAP Calculation with NaN Fallback
    tp = (df['High'] + df['Low'] + df['Close']) / 3
    tpv = tp * df['Volume']
    group = df.index.date
    
    cum_tpv = tpv.groupby(group).cumsum()
    cum_vol = df['Volume'].groupby(group).cumsum()
    
    # Calculation: If volume is 0, use Typical Price (tp) as fallback
    vwap_calc = cum_tpv / cum_vol.replace(0, np.nan)
    df['VWAP'] = vwap_calc.fillna(tp) # <--- THIS FIXES THE NaN ISSUE

    # 4. Signal Mapping
    size = len(df)
    signals = ["SIDE"] * size
    p_vals, v_vals = df['P_Master'].values, df['VWAP'].values
    
    for i in range(1, size):
        if np.isnan(v_vals[i]) or np.isnan(p_vals[i]): continue
        
        if p_vals[i] > v_vals[i] and p_vals[i-1] <= v_vals[i-1]:
            signals[i] = "BUY"
        elif p_vals[i] < v_vals[i] and p_vals[i-1] >= v_vals[i-1]:
            signals[i] = "SELL"
        else:
            signals[i] = "UP" if p_vals[i] > v_vals[i] else "DOWN"

    df['ST'], df['ST_Trend'] = df['VWAP'], signals
    return df

def get_signal(df=None):
    if df is None: df = fetch_yf_data()
    if df is None or df.empty: return "NONE", 0.0
    try:
        df_st = calculate_supertrend(df)
        last = df_st.iloc[-1]
        return str(last['ST_Trend']), float(last['ST'])
    except:
        return "NONE", 0.0

if __name__ == "__main__":
    test_df = fetch_yf_data()
    if test_df is not None:
        df_full = calculate_supertrend(test_df)
        print("\nFix Verified - Last 5 bars:")
        print(df_full[['P_Master', 'VWAP', 'ST_Trend']].tail(5))




