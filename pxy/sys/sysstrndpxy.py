import pandas as pd
import numpy as np
from sysdtafpxy import fetch_yf_data

# ==================================================
# GLOBAL CONFIG
# ==================================================
DEBUG_MODE = False

def calculate_supertrend_1_1(df: pd.DataFrame) -> pd.DataFrame:
    """
    PXY® Sync Engine:
    Logic: Fixed 1:1 SuperTrend (ATR 1, Multiplier 1.0)
    Reference: Independent Heikin-Ashi Line
    """
    df = df.copy()
    
    # 1. Independent Heikin-Ashi Line (Reference Only)
    df['HA_Close'] = (df['Open'] + df['High'] + df['Low'] + df['Close']) / 4
    
    # 2. SuperTrend 1:1 Pre-calculations (Based on Close)
    df['previous_close'] = df['Close'].shift(1)
    df['TR'] = np.maximum(df['High'] - df['Low'], 
               np.maximum(abs(df['High'] - df['previous_close']), 
                          abs(df['Low'] - df['previous_close'])))
    
    # ATR(1) is simply the TR of the current candle
    df['ATR_1'] = df['TR'] 
    df['HL2'] = (df['High'] + df['Low']) / 2
    
    size = len(df)
    st_line = [0.0] * size
    trend_state = [1] * size # 1 for UP, -1 for DOWN

    # 3. 1:1 Calculation Loop
    for i in range(size):
        curr_close = df['Close'].iloc[i]
        hl2 = df['HL2'].iloc[i]
        atr1 = df['ATR_1'].iloc[i]
        
        if i == 0:
            st_line[i] = hl2
            continue

        # Band Calculation (Multiplier 1.0)
        upper_band = hl2 + (1.0 * atr1)
        lower_band = hl2 - (1.0 * atr1)
        
        # Continuous Trailing Logic (Price vs Previous ST)
        prev_st = st_line[i-1]
        
        if curr_close > prev_st:
            trend_state[i] = 1
        elif curr_close < prev_st:
            trend_state[i] = -1
        else:
            trend_state[i] = trend_state[i-1]

        if trend_state[i] == 1:
            st_line[i] = max(lower_band, prev_st)
        else:
            st_line[i] = min(upper_band, prev_st)

    # 4. Signal Mapping (Using HA Line vs ST Line)
    # This matches your chart where HA is a reference line
    signals = ["SIDE"] * size
    for i in range(1, size):
        ha_curr = df['HA_Close'].iloc[i]
        ha_prev = df['HA_Close'].iloc[i-1]
        st_curr = st_line[i]
        st_prev = st_line[i-1]

        # Crossing Logic (HA Crosses ST)
        if ha_curr > st_curr and ha_prev <= st_prev:
            signals[i] = "BUY"
        elif ha_curr < st_curr and ha_prev >= st_prev:
            signals[i] = "SELL"
        else:
            signals[i] = "UP" if ha_curr > st_curr else "DOWN"

    df['ST'] = st_line
    df['ST_Trend'] = signals
    return df

def get_signal(df=None):
    if df is None:
        df = fetch_yf_data()
    if df is None or df.empty:
        return "NONE", 0.0
        
    df_st = calculate_supertrend_1_1(df)
    last = df_st.iloc[-1]
    return last['ST_Trend'], last['ST']

if __name__ == "__main__":
    signal_res, st_price = get_signal()
    print("-" * 35)
    print(f"PXY® 1:1 SYNC SIGNAL: {signal_res}")
    print(f"ST LINE PRICE: {st_price:.2f}")
    print("-" * 35)




