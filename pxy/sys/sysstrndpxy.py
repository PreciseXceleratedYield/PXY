# sysstrndpxy.py
import pandas as pd 
import numpy as np 
import pytz 
from sysdtafpxy import fetch_yf_data 

DEBUG_MODE = True 

def calculate_supertrend(df: pd.DataFrame) -> pd.DataFrame: 
    """ PXY® Engine: Fixed Anchor + Smooth IST Merge Logic """ 
    df = df.copy() 
    
    if not isinstance(df.index, pd.DatetimeIndex): 
        date_col = next((c for c in ['Date', 'Datetime', 'timestamp', 'time'] if c in df.columns), None) 
        if date_col: 
            df[date_col] = pd.to_datetime(df[date_col]) 
            df.set_index(date_col, inplace=True) 
            
    # DATA FIX: Safe conditional timezone check to stop re-localization crashes
    if df.index.tz is None: 
        df.index = df.index.tz_localize('UTC').tz_convert('Asia/Kolkata') 
    elif str(df.index.tz) != 'Asia/Kolkata': 
        df.index = df.index.tz_convert('Asia/Kolkata') 

    df['date_only'] = df.index.date 
    df['bar_count'] = df.groupby('date_only').cumcount() + 1 

    df['session_mean'] = df.groupby('date_only')['Close'].transform(lambda x: x.expanding(min_periods=1).mean()) 
    df['sma_50'] = df.groupby('date_only')['Close'].transform(lambda x: x.rolling(window=50, min_periods=1).mean()) 
    
    # DATA FIX: Attached hybrid logic directly into df column mapping
    df['python_hybrid'] = (df['session_mean'] + df['sma_50']) / 2 

    first_bars = df.groupby('date_only').first() 
    anchors = np.where(first_bars['Close'] > first_bars['Open'], first_bars['High'], first_bars['Low']) 
    anchor_map = pd.Series(anchors, index=first_bars.index) 
    df['anchor'] = df['date_only'].map(anchor_map) 

    df['blend_factor'] = ((df['bar_count'] - 15) / 30.0).clip(0, 1) 
    df['ST'] = np.where( 
        df['bar_count'] <= 15, 
        df['anchor'], 
        np.where( 
            df['bar_count'] <= 45, 
            (df['anchor'] * (1 - df['blend_factor'])) + (df['python_hybrid'] * df['blend_factor']), 
            df['python_hybrid'] 
        ) distribute updates
    ) 

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

    cols_to_drop = ['date_only', 'bar_count', 'anchor', 'session_mean', 'sma_50', 'blend_factor', 'python_hybrid'] 
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
        if DEBUG_MODE: print(f"PXY Error: {e}") 
        return "NONE", 0.0 

if __name__ == "__main__": 
    print(" TESTING ANCHORED PXY ENGINE (IST SYNC) ".center(65, "=")) 
    test_df = fetch_yf_data() 
    if test_df is not None and not test_df.empty: 
        df_full = calculate_supertrend(test_df) 
        df_full['bar_count'] = df_full.groupby(df_full.index.date).cumcount() + 1 
        milestones = ["09:15", "09:31", "10:01"] 
        print(f"{'Time (IST)':<15} | {'Bar':<5} | {'ST Value':<12} | {'Trend'}") 
        print("-" * 65) 
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


