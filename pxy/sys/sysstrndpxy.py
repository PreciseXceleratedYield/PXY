import pandas as pd
import numpy as np
from sysdtafpxy import fetch_yf_data

# ==================================================
# GLOBAL CONFIG
# ==================================================
DEBUG_MODE = False

def calculate_supertrend(df: pd.DataFrame) -> pd.DataFrame:
    """
    PXY® Master Engine Sync:
    Logic: VWAP Replacing ST Line
    Reference: Master Price P = (e1+e2+e3+e4)/4
    """
    df = df.copy()

    # 1. ROBUST DATETIME INDEX FIX
    # Ensures .index.date works correctly for session resets
    if not isinstance(df.index, pd.DatetimeIndex):
        date_col = None
        for col in ['Date', 'Datetime', 'timestamp', 'time', 'date']:
            if col in df.columns:
                date_col = col
                break
        
        if date_col:
            df[date_col] = pd.to_datetime(df[date_col])
            df.set_index(date_col, inplace=True)
        else:
            # Fallback: force index to datetime if it's strings/objects
            try:
                df.index = pd.to_datetime(df.index)
            except:
                pass 

    # 2. Master Price Engine (Synchronized)
    def get_p_series(df_slice):
        o = df_slice['Open']
        h = df_slice['High']
        l = df_slice['Low']
        c = df_slice['Close']
        c1 = c.shift(1)
        
        e1 = c
        e2 = (c1 + c) / 2
        e3 = (c + o) / 2
        e4 = (o + h + l + c) / 4
        return (e1 + e2 + e3 + e4) / 4

    df['P_Master'] = get_p_series(df)

    # 3. VWAP Calculation (Session Reset)
    tp = (df['High'] + df['Low'] + df['Close']) / 3
    tpv = tp * df['Volume']
    
    # Group by calendar date to reset daily
    group = df.index.date
    cum_tpv = tpv.groupby(group).cumsum()
    cum_vol = df['Volume'].groupby(group).cumsum()
    
    # Avoid division by zero if volume is 0
    df['VWAP'] = cum_tpv / cum_vol.replace(0, np.nan)
    df['VWAP'] = df['VWAP'].ffill() # Forward fill initial NaNs

    # 4. Signal Mapping (P vs VWAP)
    size = len(df)
    signals = ["SIDE"] * size
    
    # Optimized loop using numpy values to prevent indexing errors
    p_vals = df['P_Master'].values
    v_vals = df['VWAP'].values
    
    for i in range(1, size):
        p_curr, p_prev = p_vals[i], p_vals[i-1]
        v_curr, v_prev = v_vals[i], v_vals[i-1]

        # Skip if VWAP calculation hasn't started yet
        if np.isnan(v_curr) or np.isnan(v_prev):
            continue

        # Crossing Logic (Master Price P Crosses VWAP)
        if p_curr > v_curr and p_prev <= v_prev:
            signals[i] = "BUY"
        elif p_curr < v_curr and p_prev >= v_prev:
            signals[i] = "SELL"
        else:
            signals[i] = "UP" if p_curr > v_curr else "DOWN"

    df['ST'] = df['VWAP']
    df['ST_Trend'] = signals
    return df

def get_signal(df=None):
    """
    Standard interface for sysentrpxy and sysdashpxy
    """
    if df is None:
        df = fetch_yf_data()
    
    if df is None or df.empty:
        return "NONE", 0.0
        
    try:
        df_st = calculate_supertrend(df)
        if df_st.empty:
            return "NONE", 0.0
            
        last = df_st.iloc[-1]
        
        # Ensure we return valid types
        res_trend = str(last['ST_Trend']) if pd.notna(last['ST_Trend']) else "SIDE"
        res_price = float(last['ST']) if pd.notna(last['ST']) else 0.0
        
        return res_trend, res_price
        
    except Exception as e:
        if DEBUG_MODE:
            print(f"Error in sysstrndpxy calculation: {e}")
        return "NONE", 0.0

# ==================================================
# TESTER BLOCK
# ==================================================
if __name__ == "__main__":
    print(" TESTING SYSSTRNDPXY (VWAP ENGINE) ".center(50, "="))
    
    # Simulate or Fetch Data
    test_df = fetch_yf_data()
    
    if test_df is not None and not test_df.empty:
        trend, price = get_signal(test_df)
        
        print(f"Index Type: {type(test_df.index)}")
        print(f"Latest Time: {test_df.index[-1]}")
        print("-" * 50)
        print(f"RESULT TREND: {trend}")
        print(f"RESULT VWAP : {price:.2f}")
        print("-" * 50)
        
        # Show table of last 5 bars
        df_full = calculate_supertrend(test_df)
        print("\nLast 5 bars calculation:")
        print(df_full[['P_Master', 'VWAP', 'ST_Trend']].tail(5))
    else:
        print("ERROR: No data received from fetch_yf_data()")




