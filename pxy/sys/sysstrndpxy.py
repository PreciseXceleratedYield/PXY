import pandas as pd
import numpy as np
import pytz
from sysdtafpxy import fetch_yf_data

# ==================================================
# GLOBAL CONFIG
# ==================================================
DEBUG_MODE = False

def calculate_supertrend(df: pd.DataFrame) -> pd.DataFrame:
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
    # FIXED: Using transform to ensure index alignment
    session_mean = df.groupby('date_only')['Close'].transform(lambda x: x.expanding().mean())
    
    # Logic: Expanding if bars < 50, otherwise Rolling 50
    sma_50 = df.groupby('date_only')['Close'].transform(
        lambda x: x.expanding().mean() if len(x) <= 50 else x.rolling(window=50).mean()
    )
    
    python_hybrid = (session_mean + sma_50) / 2

    # 4. Anchor Logic (9:15 IST Candle)
    daily_groups = df.groupby('date_only')
    first_bars = daily_groups.first()
    anchors = np.where(first_bars['Close'] > first_bars['Open'], first_bars['High'], first_bars['Low'])
    anchor_map = pd.Series(anchors, index=first_bars.index)
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
        
        if pd.isna(curr_line):
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

if __name__ == "__main__":
    print(" TESTING ANCHORED PXY ENGINE (IST SYNC) ".center(60, "="))
    test_df = fetch_yf_data()
    
    if test_df is not None:
        df_full = calculate_supertrend(test_df)
        df_full['bar_count'] = df_full.groupby(df_full.index.date).cumcount() + 1
        
        milestones = ["09:15", "09:31", "10:01"]
        print(f"{'Time (IST)':<15} | {'Bar':<5} | {'ST Value':<12} | {'Trend'}")
        print("-" * 60)
        
        for ts in df_full.index:
            time_str = ts.strftime('%H:%M')
            if time_str in milestones:
                row = df_full.loc[ts]
                st_val = row['ST']
                trend = row['ST_Trend']
                bc = row['bar_count']
                print(f"{ts.strftime('%Y-%m-%d %H:%M'):<15} | {int(bc):<5} | {st_val:<12.2f} | {trend}")

        print("-" * 60)
        print(f"Latest Live Price: {test_df['Close'].iloc[-1]:.2f}")



