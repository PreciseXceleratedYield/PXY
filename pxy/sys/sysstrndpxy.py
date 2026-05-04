# sysstrndpxy.py
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
    Major ST (Factor: 2 * ATR)
    Minor ST (REPLACED): Dynamic SMA (Period = max(14, ATR))
    """
    df = df.copy()
    
    # 1. Vectorized Pre-calculations
    df['previous_close'] = df['Close'].shift(1)
    df['TR'] = np.maximum(df['High'] - df['Low'], 
                          np.maximum(abs(df['High'] - df['previous_close']), 
                                     abs(df['Low'] - df['previous_close'])))
    df['HL2'] = (df['High'] + df['Low']) / 2
    df['HA_Close'] = (df['Open'] + df['High'] + df['Low'] + df['Close']) / 4

    # Containers
    size = len(df)
    st_maj = [0.0] * size
    st_min = [0.0] * size # Stores Dynamic SMA
    trend_maj = ["UP"] * size
    dyn_atr = [0.0] * size

    # Seed ATR for Recursive Alpha
    seed_atr_vals = df['TR'].rolling(window=3, min_periods=1).mean()

    for i in range(size):
        tr, hl2, ha_c = df['TR'].iloc[i], df['HL2'].iloc[i], df['HA_Close'].iloc[i]
        
        if i == 0:
            dyn_atr[i] = seed_atr_vals.iloc[0] if not pd.isna(seed_atr_vals.iloc[0]) else 1.0
            st_maj[i] = hl2
            st_min[i] = df['Close'].iloc[0]
            continue

        # DYNAMIC ATR (Recursive Alpha)
        prev_atr = dyn_atr[i-1]
        alpha = 1 / max(1, round(prev_atr))
        dyn_atr[i] = (alpha * tr) + (1 - alpha) * prev_atr

        # --- MAJOR SUPERTREND LOGIC (Factor: 2 * ATR) ---
        maj_f = 2 * dyn_atr[i]
        curr_t_maj = "UP" if ha_c > st_maj[i-1] else "DOWN" if ha_c < st_maj[i-1] else trend_maj[i-1]
        
        if curr_t_maj == "UP":
            st_maj[i] = max(hl2 - maj_f, st_maj[i-1])
        else:
            st_maj[i] = min(hl2 + maj_f, st_maj[i-1])
        trend_maj[i] = curr_t_maj

        # --- MINOR DYNAMIC SMA LOGIC (Period: ATR) ---
        min_period = int(max(14, dyn_atr[i]))
        lookback = min(i + 1, min_period)
        # Calculate SMA on standard Close
        st_min[i] = df['Close'].iloc[i - lookback + 1 : i + 1].mean()

    # --- DASHBOARD SIGNAL MAPPING ---
    signals = ["SIDE"] * size
    for i in range(1, size):
        c_0, o_0, s_min_0 = df['Close'].iloc[i], df['Open'].iloc[i], st_min[i]
        c_1, o_1, s_min_1 = df['Close'].iloc[i-1], df['Open'].iloc[i-1], st_min[i-1]
        ha_c_now, s_maj_now = df['HA_Close'].iloc[i], st_maj[i]

        # BUY/SELL based on Price crossing the Dynamic SMA
        if (o_0 <= s_min_0 and c_0 > s_min_0) or (o_1 <= s_min_1 and c_0 > s_min_0):
            signals[i] = "BUY"
        elif (o_0 >= s_min_0 and c_0 < s_min_0) or (o_1 >= s_min_1 and c_0 < s_min_0):
            signals[i] = "SELL"
        # Trend continuation based on both lines
        elif ha_c_now > s_min_0 and ha_c_now > s_maj_now:
            signals[i] = "UP"
        elif ha_c_now < s_min_0 and ha_c_now < s_maj_now:
            signals[i] = "DOWN"
        else:
            signals[i] = "SIDE"

    df['ST'] = st_min            # Dashboard 'LINE' (Minor SMA)
    df['ST_Trend'] = signals      # Dashboard 'Super' (Signal)
    df['ST_Maj_Price'] = st_maj   # Target Script (Major ST)
    return df

def get_signal(df=None):
    if df is None:
        df = fetch_yf_data()
    if df is None or df.empty:
        return "NONE", 0.0
    
    df_st = calculate_supertrend(df)
    last = df_st.iloc[-1]
    
    # Return the categorical signal and the Minor SMA price
    return last['ST_Trend'], last['ST']

if __name__ == "__main__":
    # Atomic Execution
    signal_res, minor_sma_price = get_signal()
    print(f"PXY® SIG: {signal_res} | MIN_SMA_PRC: {minor_sma_price:.2f}")





