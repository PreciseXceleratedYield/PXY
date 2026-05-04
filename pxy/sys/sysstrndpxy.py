import pandas as pd
import numpy as np
from sysdtafpxy import fetch_yf_data

# ==================================================
# GLOBAL CONFIG
# ==================================================
DEBUG_MODE = False

def calculate_supertrend(df: pd.DataFrame) -> pd.DataFrame:
    """
    PXY® Engine Updated:
    Major Line: SMA with period = max(14, ATR * ATR)
    Minor Line: SMA with period = max(14, ATR)
    """
    df = df.copy()
    
    # 1. Vectorized Pre-calculations
    df['previous_close'] = df['Close'].shift(1)
    df['TR'] = np.maximum(df['High'] - df['Low'], 
                          np.maximum(abs(df['High'] - df['previous_close']), 
                                     abs(df['Low'] - df['previous_close'])))
    df['HA_Close'] = (df['Open'] + df['High'] + df['Low'] + df['Close']) / 4

    size = len(df)
    st_maj = [0.0] * size
    st_min = [0.0] * size
    dyn_atr = [0.0] * size

    # Seed ATR for Dynamic Alpha
    seed_atr_vals = df['TR'].rolling(window=3, min_periods=1).mean()

    for i in range(size):
        tr, ha_c = df['TR'].iloc[i], df['HA_Close'].iloc[i]
        
        if i == 0:
            dyn_atr[i] = seed_atr_vals.iloc[0] if not pd.isna(seed_atr_vals.iloc[0]) else 1.0
            st_maj[i], st_min[i] = df['Close'].iloc[0], df['Close'].iloc[0]
            continue

        # DYNAMIC ATR (Recursive)
        prev_atr = dyn_atr[i-1]
        alpha = 1 / max(1, round(prev_atr))
        dyn_atr[i] = (alpha * tr) + (1 - alpha) * prev_atr

        # --- MAJOR SMA (Period = ATR * ATR) ---
        maj_period = int(max(14, dyn_atr[i] * dyn_atr[i]))
        maj_lookback = min(i + 1, maj_period)
        st_maj[i] = df['Close'].iloc[i-maj_lookback+1 : i+1].mean()

        # --- MINOR SMA (Period = ATR) ---
        min_period = int(max(14, dyn_atr[i]))
        min_lookback = min(i + 1, min_period)
        st_min[i] = df['Close'].iloc[i-min_lookback+1 : i+1].mean()

    # --- SILENT DASHBOARD MAPPING ---
    signals = ["SIDE"] * size
    for i in range(1, size):
        c_0, o_0, s_min_0 = df['Close'].iloc[i], df['Open'].iloc[i], st_min[i]
        s_min_1 = st_min[i-1]
        ha_c_now, s_maj_0 = df['HA_Close'].iloc[i], st_maj[i]

        # Signal Logic based on Price vs Minor SMA and HA_Close vs Major SMA
        if (o_0 <= s_min_0 and c_0 > s_min_0):
            signals[i] = "BUY"
        elif (o_0 >= s_min_0 and c_0 < s_min_0):
            signals[i] = "SELL"
        elif ha_c_now > s_min_0 and ha_c_now > s_maj_0:
            signals[i] = "UP"
        elif ha_c_now < s_min_0 and ha_c_now < s_maj_0:
            signals[i] = "DOWN"
        else:
            signals[i] = "SIDE"

    df['ST'] = st_min            # Dashboard 'LINE'
    df['ST_Trend'] = signals      # Dashboard 'Super'
    df['ST_Maj_Price'] = st_maj   # Dashboard 'Target'
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
    signal_res, minor_sma = get_signal()
    print(f"PXY® SIG: {signal_res} | MINOR_SMA: {minor_sma:.2f}")





