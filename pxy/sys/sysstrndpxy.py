import pandas as pd
import numpy as np
import pytz
from sysdtafpxy import fetch_yf_data

# ==================================================
# GLOBAL CONFIG
# ==================================================
DEBUG_MODE = False

def calculate_supertrend(df: pd.DataFrame) -> pd.DataFrame:
    """
    PXY® Engine: Fixed Anchor + Smooth IST Merge Logic
    Synchronized with Pine Script V5.
    """
    df = df.copy()

    # 1. Robust Datetime Index Fix & IST Conversion
    if not isinstance(df.index, pd.DatetimeIndex):
        date_col = next((c for c in ['Date', 'Datetime', 'timestamp', 'time'] if c in df.columns), None)
        if date_col:
            df[date_col] = pd.to_datetime(df[date_col])
            df.set_index(date_col, inplace=True)
    
    if df.index.tz is None:
        df.index = df.index.tz_localize('UTC').tz_convert('Asia/Kolkata')
    else:
        df.index = df.index.tz_convert('Asia/Kolkata')

    # 2. Session Tracking
    df['date_only'] = df.index.date
    df['bar_count'] = df.groupby('date_only').cumcount() + 1

    # 3. Components: Session Price Mean & Dynamic 50 SMA
    session_mean = df.groupby('date_only', group_keys=False)['Close'].apply(lambda x: x.expanding().mean())
    sma_50 = df.groupby('date_only', group_keys=False)['Close'].apply(
        lambda x: x.expanding().mean() if len(x) <= 50 else x.rolling(window=50).mean()
    )
    python_hybrid = (session_mean + sma_50) / 2

    # 4. FIXED ANCHOR LOGIC (Avoids ValueError in Pandas 2.0+)
    # Determine the anchor value (High or Low) for the first bar of each day
    daily_groups = df.groupby('date_only')
    first_bars = daily_groups.first()
    
    # Logic: Bullish 9:15 -> High, Bearish -> Low
    anchors = np.where(first_bars['Close'] > first_bars['Open'], first_bars['High'], first_bars['Low'])
    anchor_map = pd.Series(anchors, index=first_bars.index)
    
    # Map the anchor back to every bar in the session
    df['anchor'] = df['date_only'].map(anchor_map)

    # 5. The No-Jump Black Line Logic (ST)
    blend_factor = (df['bar_count'] - 15) / 30.0
    
    df['ST'] = np.select(
        [
            df['bar_count'] <= 15,
            (df['bar_count'] > 15) & (df['bar_count'] <= 45)
        ],
        [
            df['anchor'],
            (df['anchor'] * (1 - blend_factor)) + (python_hybrid * blend_factor)
        ],
        default=python_hybrid
    )

    # 6. Signal Mapping
    st_trend = []
    prev_trend = "SIDE"
    for i in range(len(df)):
        curr_close = df['Close'].iloc[i]
        curr_line = df['ST'].iloc[i]
        
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
    cols_to_drop = ['date_only', 'bar_count', 'anchor']
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
        if DEBUG_MODE: print(f"White Line Error: {e}")
        return "NONE", 0.0

if __name__ == "__main__":
    print(" TESTING ANCHORED PXY ENGINE (IST SYNC) ".center(50, "="))
    test_df = fetch_yf_data()
    if test_df is not None:
        df_full = calculate_supertrend(test_df)
        print(f"Latest Price : {test_df['Close'].iloc[-1]:.2f}")
        print(f"ST Line Val  : {df_full['ST'].iloc[-1]:.2f}")
        print(f"Trend State  : {df_full['ST_Trend'].iloc[-1]}")
        print("-" * 50)
        print(df_full[['ST', 'ST_Trend']].tail(5))

