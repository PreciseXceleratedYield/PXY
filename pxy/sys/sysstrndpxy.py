import pandas as pd
import numpy as np
from sysdtafpxy import fetch_yf_data

# ==================================================
# GLOBAL CONFIG
# ==================================================
DEBUG_MODE = False

def calculate_supertrend(df: pd.DataFrame) -> pd.DataFrame:
    """
    PXY® Engine: 
    Major ST (Factor: ATR^2)
    Minor ST (REPLACED): Dynamic SMA (Period = max(14, 2 * ATR))
    """
    df = df.copy()
    
    # 1. Vectorized Pre-calculations
    df['previous_close'] = df['Close'].shift(1)
    df['TR'] = np.maximum(df['High'] - df['Low'], 
                          np.maximum(abs(df['High'] - df['previous_close']), 
                                     abs(df['Low'] - df['previous_close'])))
    df['HL2'] = (df['High'] + df['Low']) / 2
    df['HA_Close'] = (df['Open'] + df['High'] + df['Low'] + df['Close']) / 4

    size = len(df)
    st_maj = [0.0] * size
    st_min = [0.0] * size # Now stores Dynamic SMA
    trend_maj = ["UP"] * size
    dyn_atr = [0.0] * size

    seed_atr_vals = df['TR'].rolling(window=3, min_periods=1).mean()

    for i in range(size):
        tr, hl2, ha_c = df['TR'].iloc[i], df['HL2'].iloc[i], df['HA_Close'].iloc[i]
        
        if i == 0:
            dyn_atr[i] = seed_atr_vals.iloc[0] if not pd.isna(seed_atr_vals.iloc[0]) else 1.0
            st_maj[i], st_min[i] = hl2, df['Close'].iloc[i]
            continue

        # DYNAMIC ATR (Recursive Alpha)
        prev_atr = dyn_atr[i-1]
        alpha = 1 / max(1, round(prev_atr))
        dyn_atr[i] = (alpha * tr) + (1 - alpha) * prev_atr

        # MAJOR ST LOGIC
        maj_f = dyn_atr[i] * dyn_atr[i]
        curr_t_maj = "UP" if ha_c > st_maj[i-1] else "DOWN" if ha_c < st_maj[i-1] else trend_maj[i-1]
        st_maj[i] = max(hl2 - maj_f, st_maj[i-1]) if curr_t_maj == "UP" else min(hl2 + maj_f, st_maj[i-1])
        trend_maj[i] = curr_t_maj

        # REPLACEMENT: DYNAMIC SMA LOGIC
        # Period = max(14, 2 * ATR)
        dyn_period = int(max(14, 2 * dyn_atr[i]))
        
        # Ensure we don't look back further than available data
        lookback = min(i + 1, dyn_period)
        st_min[i] = df['Close'].iloc[i-lookback+1 : i+1].mean()

    # --- SILENT DASHBOARD MAPPING ---
    signals = ["SIDE"] * size
    for i in range(1, size):
        c_0, o_0, s_0 = df['Close'].iloc[i], df['Open'].iloc[i], st_min[i]
        c_1, o_1, s_1 = df['Close'].iloc[i-1], df['Open'].iloc[i-1], st_min[i-1]
        ha_c_now, maj_now = df['HA_Close'].iloc[i], st_maj[i]

        if (o_0 <= s_0 and c_0 > s_0) or (o_1 <= s_1 and c_0 > s_0):
            signals[i] = "BUY"
        elif (o_0 >= s_0 and c_0 < s_0) or (o_1 >= s_1 and c_0 < s_0):
            signals[i] = "SELL"
        elif ha_c_now > s_0 and ha_c_now > maj_now:
            signals[i] = "UP"
        elif ha_c_now < s_0 and ha_c_now < maj_now:
            signals[i] = "DOWN"
        else:
            signals[i] = "SIDE"

    df['ST'] = st_min 
    df['ST_Trend'] = signals 
    df['ST_Maj_Price'] = st_maj 
    return df

def get_signal(df=None):
    if df is None:
        df = fetch_yf_data()
    if df is None or df.empty:
        return "NONE", 0.0
    df_st = calculate_supertrend(df)
    last = df_st.iloc[-1]
    return last['ST_Trend'], last['ST']

if __name__ == "__main__":
    signal_res, sma_val = get_signal()
    print(f"PXY® SIG: {signal_res} | DYN_SMA_PRC: {sma_val:.2f}")




