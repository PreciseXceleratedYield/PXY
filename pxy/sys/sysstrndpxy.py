import pandas as pd
import numpy as np
from sysdtafpxy import fetch_yf_data

# ==================================================
# GLOBAL CONFIG
# ==================================================
DEBUG_MODE = False

def calculate_supertrend(df: pd.DataFrame) -> pd.DataFrame:
    """
    PXY® Engine: White Line Logic (No-Volume Version)
    - Line = (Session Mean + Dynamic 50 SMA) / 2
    - Logic handles the YF 'Zero Volume' issue by using session price mean as proxy.
    """
    df = df.copy()

    # 1. ROBUST DATETIME INDEX FIX
    if not isinstance(df.index, pd.DatetimeIndex):
        date_col = next((c for c in ['Date', 'Datetime', 'timestamp', 'time'] if c in df.columns), None)
        if date_col:
            df[date_col] = pd.to_datetime(df[date_col])
            df.set_index(date_col, inplace=True)

    # 2. Session Tracking
    df['date_only'] = df.index.date
    df['bar_count'] = df.groupby('date_only').cumcount() + 1

    # 3. Session Price Mean (Proxy for VWAP when volume is 0)
    # This is the cumulative average of price since the 9:15 open
    session_mean = df.groupby('date_only', group_keys=False)['Close'].apply(
        lambda x: x.expanding(min_periods=1).mean()
    )

    # 4. Dynamic 50 SMA Calculation (Session-based)
    # Window grows from 1 to 50 as bars accumulate today
    sma_50 = df.groupby('date_only', group_keys=False)['Close'].apply(
        lambda x: x.expanding(min_periods=1).mean() if len(x) <= 50 else x.rolling(window=50).mean()
    )

    # 5. White Line Average (Mean of the two session averages)
    df['ST'] = (session_mean + sma_50) / 2

    # 6. Signal Mapping (Retaining BUY/UP/SELL/DOWN for downstream)
    st_trend = []
    prev_trend = "SIDE"
    
    for i in range(len(df)):
        curr_close = df['Close'].iloc[i]
        curr_line = df['ST'].iloc[i]
        
        # Handle initial NaNs
        if np.isnan(curr_line):
            st_trend.append("SIDE")
            continue
            
        if curr_close > curr_line:
            new_trend = "UP" if prev_trend in ["UP", "BUY"] else "BUY"
        elif curr_close < curr_line:
            new_trend = "DOWN" if prev_trend in ["DOWN", "SELL"] else "SELL"
        else:
            new_trend = "SIDE"
            
        st_trend.append(new_trend)
        prev_trend = new_trend

    df['ST_Trend'] = st_trend
    
    # Cleanup temporary columns
    cols_to_drop = ['date_only', 'bar_count']
    df.drop(columns=[c for c in cols_to_drop if c in df.columns], inplace=True)
    
    return df

def get_signal(df=None):
    """Main entry point for downstream modules."""
    if df is None:
        df = fetch_yf_data()
    if df is None or df.empty:
        return "NONE", 0.0
    try:
        df_st = calculate_supertrend(df)
        last = df_st.iloc[-1]
        # Return Signal string and Line value float
        return str(last['ST_Trend']), float(last['ST'])
    except Exception as e:
        if DEBUG_MODE:
            print(f"White Line Error: {e}")
        return "NONE", 0.0

if __name__ == "__main__":
    print(" TESTING NO-VOLUME WHITE LINE ENGINE ".center(50, "="))
    test_df = fetch_yf_data()
    if test_df is not None:
        df_full = calculate_supertrend(test_df)
        print(f"Latest Price : {test_df['Close'].iloc[-1]:.2f}")
        print(f"White Line   : {df_full['ST'].iloc[-1]:.2f}")
        print(f"Signal State : {df_full['ST_Trend'].iloc[-1]}")
        print("-" * 50)
        print(df_full[['ST', 'ST_Trend']].tail(5))




