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
    print(" TESTING ANCHORED PXY ENGINE (IST SYNC) ".center(60, "="))
    test_df = fetch_yf_data()
    
    if test_df is not None:
        df_full = calculate_supertrend(test_df)
        
        # 1. Add bar_count back temporarily for printing if you dropped it in cleanup
        # If already dropped, we re-calculate it locally for the print
        df_full['bar_count'] = df_full.groupby(df_full.index.date).cumcount() + 1
        
        # 2. Define our cross-check milestones
        milestones = ["09:15", "09:31", "10:01"]
        
        print(f"{'Time (IST)':<15} | {'Bar':<5} | {'ST Value':<12} | {'Trend'}")
        print("-" * 50)
        
        # 3. Filter and Print
        for ts in df_full.index:
            time_str = ts.strftime('%H:%M')
            if time_str in milestones:
                row = df_full.loc[ts]
                # If ST is a Series (multiple days), we take the last one
                st_val = row['ST'] if isinstance(row['ST'], (float, np.float64)) else row['ST'].iloc[-1]
                trend = row['ST_Trend'] if isinstance(row['ST_Trend'], str) else row['ST_Trend'].iloc[-1]
                bc = row['bar_count'] if isinstance(row['bar_count'], (int, np.int64)) else row['bar_count'].iloc[-1]
                
                print(f"{ts.strftime('%Y-%m-%d %H:%M'):<15} | {int(bc):<5} | {st_val:<12.2f} | {trend}")

        print("-" * 50)
        print(f"Latest Live Price: {test_df['Close'].iloc[-1]:.2f}")


