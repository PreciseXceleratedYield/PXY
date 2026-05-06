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
    - Anchor at 9:15 IST (Hi if Bullish, Lo if Bearish)
    - Flat until 9:30 IST (Bar 15)
    - Smooth merge until 10:00 IST (Bar 45)
    - Full Sync post 10:00 (Bar 46+)
    """
    df = df.copy()

    # 1. Robust Datetime Index & IST Conversion
    if not isinstance(df.index, pd.DatetimeIndex):
        date_col = next((c for c in ['Date', 'Datetime', 'timestamp', 'time'] if c in df.columns), None)
        if date_col:
            df[date_col] = pd.to_datetime(df[date_col])
            df.set_index(date_col, inplace=True)
    
    # Force IST for consistent milestone tracking
    if df.index.tz is None:
        df.index = df.index.tz_localize('UTC').tz_convert('Asia/Kolkata')
    else:
        df.index = df.index.tz_convert('Asia/Kolkata')

    # 2. Session Tracking
    df['date_only'] = df.index.date
    df['bar_count'] = df.groupby('date_only').cumcount() + 1

    # 3. Components: Session Price Mean & Dynamic 50 SMA
    # min_periods=1 ensures no NaNs during the morning warm-up
    df['session_mean'] = df.groupby('date_only')['Close'].transform(lambda x: x.expanding(min_periods=1).mean())
    df['sma_50'] = df.groupby('date_only')['Close'].transform(lambda x: x.rolling(window=50, min_periods=1).mean())
    
    python_hybrid = (df['session_mean'] + df['sma_50']) / 2

    # 4. Anchor Logic (9:15 IST Candle)
    # Using first() to grab the 9:15 candle for each session
    first_bars = df.groupby('date_only').first()
    # Bullish -> High anchor, Bearish -> Low anchor
    anchors = np.where(first_bars['Close'] > first_bars['Open'], first_bars['High'], first_bars['Low'])
    anchor_map = pd.Series(anchors, index=first_bars.index)
    df['anchor'] = df['date_only'].map(anchor_map)

    # 5. The No-Jump Black Line Logic (ST)
    # Phase 2 merge factor: 0.0 at bar 15, 1.0 at bar 45
    df['blend_factor'] = ((df['bar_count'] - 15) / 30.0).clip(0, 1)
    
    df['ST'] = np.where(
        df['bar_count'] <= 15, 
        df['anchor'], 
        np.where(
            df['bar_count'] <= 45, 
            (df['anchor'] * (1 - df['blend_factor'])) + (python_hybrid * df['blend_factor']), 
            python_hybrid
        )
    )

    # 6. Signal Mapping (BUY/UP/SELL/DOWN)
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

    # Cleanup internal columns before return
    cols_to_drop = ['date_only', 'bar_count', 'anchor', 'session_mean', 'sma_50', 'blend_factor', 'python_hybrid']
    df.drop(columns=[c for c in cols_to_drop if c in df.columns], inplace=True)
    return df

def get_signal(df=None):
    """Main entry point for sysentrpxy.py"""
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
            print(f"PXY Error: {e}")
        return "NONE", 0.0

if __name__ == "__main__":
    print(" TESTING ANCHORED PXY ENGINE (IST SYNC) ".center(65, "="))
    test_df = fetch_yf_data()
    
    if test_df is not None:
        df_full = calculate_supertrend(test_df)
        
        # Temporary bar count for the milestone printout
        df_full['bar_count'] = df_full.groupby(df_full.index.date).cumcount() + 1
        
        milestones = ["09:15", "09:31", "10:01"]
        print(f"{'Time (IST)':<15} | {'Bar':<5} | {'ST Value':<12} | {'Trend'}")
        print("-" * 65)
        
        # Filter for latest day milestones
        latest_day = df_full.index.date[-1]
        session_df = df_full[df_full.index.date == latest_day]
        
        for ts in session_df.index:
            time_str = ts.strftime('%H:%M')
            if time_str in milestones:
                row = session_df.loc[ts]
                print(f"{ts.strftime('%Y-%m-%d %H:%M'):<15} | {int(row['bar_count']):<5} | {row['ST']:<12.2f} | {row['ST_Trend']}")

        print("-" * 65)
        print(f"Latest Price: {test_df['Close'].iloc[-1]:.2f}")
        print(f"Final Signal: {get_signal(test_df)}")




