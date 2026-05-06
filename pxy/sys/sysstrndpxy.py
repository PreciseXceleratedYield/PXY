import pandas as pd
import numpy as np
from sysdtafpxy import fetch_yf_data

# ==================================================
# GLOBAL CONFIG
# ==================================================
DEBUG_MODE = False

def calculate_supertrend(df: pd.DataFrame) -> pd.DataFrame:
    """
    PXY® Engine: Replaced SuperTrend with 'White Line' Logic
    - White Line = (VWAP + Dynamic 50 SMA) / 2
    - Signals: BUY if Price > White Line, SELL if Price < White Line
    """
    df = df.copy()

    # 1. ROBUST DATETIME INDEX FIX
    if not isinstance(df.index, pd.DatetimeIndex):
        date_col = next((c for c in ['Date', 'Datetime', 'timestamp', 'time'] if c in df.columns), None)
        if date_col:
            df[date_col] = pd.to_datetime(df[date_col])
            df.set_index(date_col, inplace=True)

    # 2. VWAP Calculation (Session-based)
    # Resetting cumulative values based on date change
    df['date_only'] = df.index.date
    hlc3 = (df['High'] + df['Low'] + df['Close']) / 3
    volume = df['Volume']
    
    df['pv'] = hlc3 * volume
    df['cum_pv'] = df.groupby('date_only')['pv'].transform(pd.Series.cumsum)
    df['cum_vol'] = df.groupby('date_only')['volume'].transform(pd.Series.cumsum)
    vwap = df['cum_pv'] / df['cum_vol']

    # 3. Dynamic 50 SMA Calculation (Session-based)
    # Grows from 1 to 50 as bars accumulate today
    df['bar_count'] = df.groupby('date_only').cumcount() + 1
    
    # Efficient calculation of expanding-to-50 SMA
    def dynamic_sma(group):
        return group['Close'].expanding(min_periods=1).mean().where(
            group['bar_count'] <= 50, 
            group['Close'].rolling(window=50).mean()
        )
    
    sma_50 = df.groupby('date_only', group_keys=False).apply(dynamic_sma)

    # 4. White Line Average (VWAP + SMA) / 2
    white_line = (vwap + sma_50) / 2

    # 5. Signal Mapping (Matching downstream expectations)
    # BUY if Close > White Line, SELL if Close < White Line
    df['ST'] = white_line
    
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
    
    # Cleanup temporary columns
    df.drop(columns=['date_only', 'pv', 'cum_pv', 'cum_vol', 'bar_count'], inplace=True, errors='ignore')
    
    return df

def get_signal(df=None):
    """Retains original signature for downstream compatibility."""
    if df is None:
        df = fetch_yf_data()
    if df is None or df.empty:
        return "NONE", 0.0
    try:
        df_st = calculate_supertrend(df)
        last = df_st.iloc[-1]
        # Returns (Signal, LineValue) exactly as before
        return str(last['ST_Trend']), float(last['ST'])
    except Exception as e:
        if DEBUG_MODE:
            print(f"White Line Signal Error: {e}")
        return "NONE", 0.0

if __name__ == "__main__":
    print(" TESTING WHITE LINE (VWAP + 50 SMA) ENGINE ".center(50, "="))
    test_df = fetch_yf_data()
    if test_df is not None:
        df_full = calculate_supertrend(test_df)
        print(f"Latest Price : {test_df['Close'].iloc[-1]:.2f}")
        print(f"White Line   : {df_full['ST'].iloc[-1]:.2f}")
        print(f"Signal State : {df_full['ST_Trend'].iloc[-1]}")
        print("-" * 50)
        print(df_full[['ST', 'ST_Trend']].tail(5))



