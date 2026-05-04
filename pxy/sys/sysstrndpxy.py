import pandas as pd
import numpy as np
from sysdtafpxy import fetch_yf_data

# ==================================================
# GLOBAL CONFIG
# ==================================================
DEBUG_MODE = False

def rma(series, length):
    """TradingView Running Moving Average (RMA) logic for ATR sync"""
    alpha = 1 / length
    result = np.zeros_like(series)
    for i in range(len(series)):
        if i == 0:
            result[i] = series[i]
        else:
            result[i] = alpha * series[i] + (1 - alpha) * result[i-1]
    return result

def calculate_supertrend(df: pd.DataFrame) -> pd.DataFrame:
    """
    PXY® Tiered Engine:
    Logic: Tiered Volatility (1.0, 2.0, 3.0) based on 3-period ATR
    Style: Continuous 'No-Jump'
    """
    df = df.copy()
    
    # 1. Vectorized Pre-calculations
    df['previous_close'] = df['Close'].shift(1)
    df['TR'] = np.maximum(df['High'] - df['Low'], 
               np.maximum(abs(df['High'] - df['previous_close']), 
                          abs(df['Low'] - df['previous_close'])))
    df['HL2'] = (df['High'] + df['Low']) / 2
    df['HA_Close'] = (df['Open'] + df['High'] + df['Low'] + df['Close']) / 4
    
    # Baseline: 3-period RMA (Sync with Pine ta.atr(3))
    df['ATR_3'] = rma(df['TR'].fillna(0).values, 3)

    size = len(df)
    st_line = [0.0] * size
    trend_state = [1] * size 
    dyn_atr_val = [0.0] * size

    for i in range(size):
        hl2 = df['HL2'].iloc[i]
        ha_c = df['HA_Close'].iloc[i]
        tr_curr = df['TR'].iloc[i]
        avg_atr = df['ATR_3'].iloc[i]

        if i == 0:
            st_line[i] = hl2
            dyn_atr_val[i] = tr_curr
            continue

        # 2. TIERED VOLATILITY ENGINE (3-Period Base)
        if tr_curr > (avg_atr * 1.5):
            dynamic_val = 1.0  # Fast
        elif tr_curr > (avg_atr * 0.8):
            dynamic_val = 2.0  # Medium
        else:
            dynamic_val = 3.0  # Slow

        # 3. DYNAMIC SMOOTHING (Alpha synced to Tier)
        alpha = 1 / dynamic_val
        dyn_atr_val[i] = (alpha * tr_curr) + (1 - alpha) * dyn_atr_val[i-1]
        
        # 4. BAND CALCULATION
        factor = dyn_atr_val[i] * dynamic_val
        upper_band = hl2 + factor
        lower_band = hl2 - factor

        # 5. CONTINUOUS TRAILING LOGIC
        prev_st = st_line[i-1]
        if ha_c > prev_st:
            trend_state[i] = 1
        elif ha_c < prev_st:
            trend_state[i] = -1
        else:
            trend_state[i] = trend_state[i-1]

        if trend_state[i] == 1:
            st_line[i] = max(lower_band, prev_st)
        else:
            st_line[i] = min(upper_band, prev_st)

    # --- DASHBOARD MAPPING ---
    signals = ["SIDE"] * size
    for i in range(1, size):
        ha_c_curr = df['HA_Close'].iloc[i]
        if trend_state[i] == 1:
            signals[i] = "UP" if ha_c_curr > st_line[i] else "BUY"
        else:
            signals[i] = "DOWN" if ha_c_curr < st_line[i] else "SELL"

    df['ST'] = st_line
    df['ST_Trend'] = signals
    df['ST_Maj_Price'] = st_line
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
    signal_res, st_price = get_signal()
    print("-" * 35)
    print(f"PXY® TIERED SIGNAL: {signal_res}")
    print(f"ST LINE PRICE: {st_price:.2f}")
    print("-" * 35)





