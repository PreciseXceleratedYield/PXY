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

def get_linreg(series_slice):
    """Pine Script ta.linreg(source, length, 0) logic"""
    length = len(series_slice)
    if length < 2: return series_slice[-1]
    x = np.arange(length)
    slope, intercept = np.polyfit(x, series_slice, 1)
    return slope * (length - 1) + intercept

def calculate_supertrend(df: pd.DataFrame) -> pd.DataFrame:
    """
    PXY® Engine:
    Logic: Dynamic Period (14 - ATR)
    Volatility: TSMA (Linear Regression)
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
    
    # Use RMA for sync with TradingView ATR
    df['ATR_base'] = rma(df['TR'].fillna(0).values, 14)

    # Containers
    size = len(df)
    st_line = [0.0] * size
    trend_state = [1] * size # 1 for UP, -1 for DOWN

    for i in range(size):
        hl2 = df['HL2'].iloc[i]
        ha_c = df['HA_Close'].iloc[i]
        
        if i == 0:
            st_line[i] = hl2
            continue

        # 2. DYNAMIC PERIOD LOGIC (x = 14 - ATR)
        atr_now = df['ATR_base'].iloc[i]
        dynamic_x = int(max(2, round(14 - atr_now)))
        
        # 3. TSMA VOLATILITY
        if i >= dynamic_x:
            tr_slice = df['TR'].iloc[i - dynamic_x + 1 : i + 1].values
            tsma_vol = get_linreg(tr_slice)
        else:
            tsma_vol = df['TR'].iloc[:i+1].mean()

        multiplier = 3.0
        upper_band = hl2 + (multiplier * tsma_vol)
        lower_band = hl2 - (multiplier * tsma_vol)

        # 4. CONTINUOUS TRAILING LOGIC (No Jumping)
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
        df = fetch_yf_data() # Real call to your data function
    if df is None or df.empty:
        return "NONE", 0.0
    
    df_st = calculate_supertrend(df)
    last = df_st.iloc[-1]
    return last['ST_Trend'], last['ST']

# ==========================================
# REAL CALL EXECUTION
# ==========================================
if __name__ == "__main__":
    signal_res, st_price = get_signal()
    print("-" * 35)
    print(f"PXY® LIVE SIGNAL: {signal_res}")
    print(f"ST LINE PRICE:  {st_price:.2f}")
    print("-" * 35)




