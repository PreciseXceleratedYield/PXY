import pandas as pd
import numpy as np
from sysdtafpxy import fetch_yf_data

# ==================================================
# GLOBAL CONFIG
# ==================================================
DEBUG_MODE = False

def calculate_supertrend(df: pd.DataFrame) -> pd.DataFrame:
    """
    PXY® SuperTrend Engine (ATR:ATR Logic):
    - Factor = Current ATR
    - Period = Current ATR (Rounded)
    """
    df = df.copy()

    # 1. ROBUST DATETIME INDEX FIX
    if not isinstance(df.index, pd.DatetimeIndex):
        date_col = next((c for c in ['Date', 'Datetime', 'timestamp', 'time'] if c in df.columns), None)
        if date_col:
            df[date_col] = pd.to_datetime(df[date_col])
            df.set_index(date_col, inplace=True)

    # 2. ATR Calculation (Standard 14-period to derive the dynamic Factor/Period)
    high = df['High']
    low = df['Low']
    close = df['Close']
    
    tr = pd.concat([high - low, 
                    (high - close.shift(1)).abs(), 
                    (low - close.shift(1)).abs()], axis=1).max(axis=1)
    
    # We use a base 14-period ATR to determine the "ATR:ATR" values
    base_atr = tr.rolling(window=14).mean()
    
    # 3. SuperTrend with ATR:ATR Logic
    # We loop to apply the dynamic nature of the Factor/Period
    size = len(df)
    st_line = np.zeros(size)
    st_trend = ["SIDE"] * size
    upper_band = np.zeros(size)
    lower_band = np.zeros(size)
    trend = 1 # 1 for Up, -1 for Down

    for i in range(1, size):
        # ATR:ATR values
        current_atr = base_atr.iloc[i]
        if np.isnan(current_atr):
            continue
            
        factor = current_atr
        # Use current ATR as period (minimum 2 to avoid errors)
        dynamic_period = max(int(round(current_atr)), 2)
        
        # Calculate hl2
        hl2 = (high.iloc[i] + low.iloc[i]) / 2
        
        # Basic Bands
        basic_ub = hl2 + (factor * current_atr)
        basic_lb = hl2 - (factor * current_atr)
        
        # Final Bands
        upper_band[i] = basic_ub if (basic_ub < upper_band[i-1] or close.iloc[i-1] > upper_band[i-1]) else upper_band[i-1]
        lower_band[i] = basic_lb if (basic_lb > lower_band[i-1] or close.iloc[i-1] < lower_band[i-1]) else lower_band[i-1]
        
        # Strategy Logic
        if trend == 1:
            if close.iloc[i] <= lower_band[i]:
                trend = -1
                st_line[i] = upper_band[i]
            else:
                st_line[i] = lower_band[i]
        else:
            if close.iloc[i] >= upper_band[i]:
                trend = 1
                st_line[i] = lower_band[i]
            else:
                st_line[i] = upper_band[i]
                
        # Trend Mapping
        if trend == 1:
            st_trend[i] = "BUY" if (st_trend[i-1] == "DOWN" or st_trend[i-1] == "SIDE") else "UP"
        else:
            st_trend[i] = "SELL" if (st_trend[i-1] == "UP" or st_trend[i-1] == "SIDE") else "DOWN"

    df['ST'] = st_line
    df['ST_Trend'] = st_trend
    return df

def get_signal(df=None):
    if df is None:
        df = fetch_yf_data()
    if df is None or df.empty:
        return "NONE", 0.0
    try:
        df_st = calculate_supertrend(df)
        last = df_st.iloc[-1]
        return str(last['ST_Trend']), float(last['ST'])
    except Exception as e:
        if DEBUG_MODE:
            print(f"SuperTrend Error: {e}")
        return "NONE", 0.0

if __name__ == "__main__":
    print(" TESTING SUPERTREND ATR:ATR ENGINE ".center(50, "="))
    test_df = fetch_yf_data()
    if test_df is not None:
        df_full = calculate_supertrend(test_df)
        print(f"Latest Price: {test_df['Close'].iloc[-1]:.2f}")
        print(f"ST Line     : {df_full['ST'].iloc[-1]:.2f}")
        print(f"Trend State : {df_full['ST_Trend'].iloc[-1]}")
        print("-" * 50)
        print(df_full[['ST', 'ST_Trend']].tail(5))





