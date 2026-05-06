import pandas as pd
import numpy as np
from sysdtafpxy import fetch_yf_data

# ==================================================
# GLOBAL CONFIG
# ==================================================
DEBUG_MODE = False

def calculate_supertrend(df: pd.DataFrame) -> pd.DataFrame:
    """
    PXY® Engine: White Line Logic (VWAP + Dynamic 50 SMA) / 2
    Fixed: Capitalization for 'Volume' column to prevent KeyError.
    """
    df = df.copy()

    # 1. ROBUST DATETIME INDEX FIX
    if not isinstance(df.index, pd.DatetimeIndex):
        date_col = next((c for c in ['Date', 'Datetime', 'timestamp', 'time'] if c in df.columns), None)
        if date_col:
            df[date_col] = pd.to_datetime(df[date_col])
            df.set_index(date_col, inplace=True)

    # 2. VWAP Calculation (Session-based)
    # Identify Volume column (handle 'Volume' or 'volume')
    vol_col = 'Volume' if 'Volume' in df.columns else 'volume'
    
    if vol_col not in df.columns:
        # Fallback if Volume is missing: use SMA only
        df['date_only'] = df.index.date
        vwap = df['Close'].rolling(window=1).mean() # Dummy vwap
    else:
        df['date_only'] = df.index.date
        hlc3 = (df['High'] + df['Low'] + df['Close']) / 3
        df['pv'] = hlc3 * df[vol_col]
        df['cum_pv'] = df.groupby('date_only')['pv'].transform(pd.Series.cumsum)
        df['cum_vol'] = df.groupby('date_only')[vol_col].transform(pd.Series.cumsum)
        vwap = df['cum_pv'] / df['cum_vol']

    # 3. Dynamic 50 SMA Calculation (Session-based)
    df['bar_count'] = df.groupby('date_only').cumcount() + 1
    
    # Efficient expanding-to-50 SMA
    sma_50 = df.groupby('date_only', group_keys=False)['Close'].apply(
        lambda x: x.expanding(min_periods=1).mean() if len(x) <= 50 else x.rolling(window=50).mean()
    )

    # 4. White Line Average
    df['ST'] = (vwap + sma_50) / 2

    # 5. Signal Mapping
    st_trend = []
    prev_trend = "SIDE"
    
    for i in range(len(df)):
        curr_close = df['Close'].iloc[i]
        curr_line = df['ST'].iloc[i]
        
        if curr_close > curr_line:
            new_trend = "UP" if prev_trend in ["UP", "BUY"] else "BUY"
        elif curr_close < curr_line:
            new_trend = "DOWN" if prev_trend in ["DOWN", "SELL"] else "SELL"
        else:
            new_trend = "SIDE"
            
        st_trend.append(new_trend)
        prev_trend = new_trend

    df['ST_Trend'] = st_trend
    
    # Cleanup
    cols_to_drop = ['date_only', 'pv', 'cum_pv', 'cum_vol', 'bar_count']
    df.drop(columns=[c for c in cols_to_drop if c in df.columns], inplace=True)
    
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
            print(f"White Line Error: {e}")
        return "NONE", 0.0

if __name__ == "__main__":
    test_df = fetch_yf_data()
    if test_df is not None:
        df_full = calculate_supertrend(test_df)
        print(f"Latest Signal: {df_full['ST_Trend'].iloc[-1]} | Value: {df_full['ST'].iloc[-1]:.2f}")



