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
    """
    df = df.copy()

    # 1. IST DATETIME FIX
    if not isinstance(df.index, pd.DatetimeIndex):
        date_col = next((c for c in ['Date', 'Datetime', 'timestamp', 'time'] if c in df.columns), None)
        if date_col:
            df[date_col] = pd.to_datetime(df[date_col])
            df.set_index(date_col, inplace=True)
    
    # Ensure index is in IST
    if df.index.tz is None:
        df.index = df.index.tz_localize('UTC').tz_convert('Asia/Kolkata')
    else:
        df.index = df.index.tz_convert('Asia/Kolkata')

    # 2. Session Tracking
    df['date_only'] = df.index.date
    df['bar_count'] = df.groupby('date_only').cumcount() + 1

    # 3. Components: Session Price Mean & Dynamic 50 SMA
    session_mean = df.groupby('date_only')['Close'].expanding().mean().reset_index(level=0, drop=True)
    
    sma_50 = df.groupby('date_only')['Close'].apply(
        lambda x: x.expanding().mean() if len(x) <= 50 else x.rolling(window=50).mean()
    ).reset_index(level=0, drop=True)

    python_hybrid = (session_mean + sma_50) / 2

    # 4. Anchor Logic (9:15 IST Candle)
    def compute_anchor(group):
        first_row = group.iloc[0]
        # Bullish 9:15 -> High, Bearish -> Low
        anchor_val = first_row['High'] if first_row['Close'] > first_row['Open'] else first_row['Low']
        return pd.Series([anchor_val] * len(group), index=group.index)

    df['anchor'] = df.groupby('date_only', group_keys=False).apply(compute_anchor)

    # 5. The No-Jump Black Line Logic (ST) using IST milestones
    # Phase 1: 9:15-9:30 | Phase 2: 9:30-10:00 (Merge) | Phase 3: Post 10:00
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
    test_df = fetch_yf_data()
    if test_df is not None:
        df_full = calculate_supertrend(test_df)
        print(f"IST Sync Check - Latest ST: {df_full['ST'].iloc[-1]:.2f}")





