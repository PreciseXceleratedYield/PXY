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
    Corrected for Pandas alignment and IST session synchronization.
    """
    df = df.copy()

    # 1. Robust Datetime Index & IST Conversion
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
    # Using groupby transform to maintain index alignment
    df['session_mean'] = df.groupby('date_only')['Close'].transform(lambda x: x.expanding().mean())
    df['sma_50'] = df.groupby('date_only')['Close'].transform(
        lambda x: x.expanding().mean() if len(x) <= 50 else x.rolling(window=50).mean()
    )
    df['python_hybrid'] = (df['session_mean'] + df['sma_50']) / 2

    # 4. Anchor Logic (9:15 IST Candle)
    first_bars = df.groupby('date_only').first()
    anchors = np.where(first_bars['Close'] > first_bars['Open'], first_bars['High'], first_bars['Low'])
    anchor_map = pd.Series(anchors, index=first_bars.index)
    df['anchor'] = df['date_only'].map(anchor_map)

    # 5. The No-Jump Black Line Logic (ST)
    df['blend_factor'] = (df['bar_count'] - 15) / 30.0
    
    # Calculate Phase transitions
    df['ST'] = np.where(
        df['bar_count'] <= 15, 
        df['anchor'], 
        np.where(
            df['bar_count'] <= 45, 
            (df['anchor'] * (1 - df['blend_factor'])) + (df['python_hybrid'] * df['blend_factor']), 
            df['python_hybrid']
        )
    )

    # 6. Signal Mapping (Trend)
    df['p_price'] = ((df['Close'] + (df['Close'] + df['Close'].shift(1))/2 + (df['Close'] + df['Open'])/2 + 
                     (df['Open'] + df['High'] + df['Low'] + df['Close'])/4) / 4).round(4)
    
    df['p_diff'] = df.groupby('date_only')['p_price'].diff()
    
    # Simple state logic based on price relative to ST
    df['ST_Trend'] = np.where(df['Close'] > df['ST'], "UP", "DOWN")
    
    return df

if __name__ == "__main__":
    print(" TESTING ANCHORED PXY ENGINE (IST SYNC) ".center(65, "="))
    test_df = fetch_yf_data()
    
    if test_df is not None:
        df_full = calculate_supertrend(test_df)
        
        milestones = ["09:15", "09:31", "10:01"]
        print(f"{'Time (IST)':<15} | {'Bar':<5} | {'ST Value':<12} | {'Trend'}")
        print("-" * 65)
        
        # Cross-check for the most recent session
        latest_date = df_full.index.date[-1]
        session_df = df_full[df_full.index.date == latest_date]
        
        for ts in session_df.index:
            time_str = ts.strftime('%H:%M')
            if time_str in milestones:
                row = session_df.loc[ts]
                print(f"{ts.strftime('%Y-%m-%d %H:%M'):<15} | {int(row['bar_count']):<5} | {row['ST']:<12.2f} | {row['ST_Trend']}")

        print("-" * 65)
        print(f"Latest Live Price: {test_df['Close'].iloc[-1]:.2f}")




