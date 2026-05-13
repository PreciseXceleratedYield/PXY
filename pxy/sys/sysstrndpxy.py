# sysstrndpxy.py 
import pandas as pd 
import numpy as np 
import pytz 
from sysdtafpxy import fetch_yf_data 

DEBUG_MODE = True 

def calculate_supertrend(df: pd.DataFrame) -> pd.DataFrame: 
    """ 
    PXY® Engine: Fixed Anchor + Smooth IST Merge Logic 
    Fully optimized to run on an unsliced continuous data stream.
    """ 
    df = df.copy() 
    if not isinstance(df.index, pd.DatetimeIndex): 
        date_col = next((c for c in ['Date', 'Datetime', 'timestamp', 'time'] if c in df.columns), None) 
        if date_col: 
            df[date_col] = pd.to_datetime(df[date_col]) 
            df.set_index(date_col, inplace=True) 
            
    # Timezone conversion check to prevent re-localization index crashes
    if df.index.tz is None: 
        df.index = df.index.tz_localize('UTC').tz_convert('Asia/Kolkata') 
    elif str(df.index.tz) != 'Asia/Kolkata': 
        df.index = df.index.tz_convert('Asia/Kolkata') 

    df['date_only'] = df.index.date 
    df['bar_count'] = df.groupby('date_only').cumcount() + 1 
    
    # Expanding session mean calculation matching Pine Script's cumulative sum loop
    df['session_mean'] = df.groupby('date_only')['Close'].transform(lambda x: x.expanding(min_periods=1).mean()) 
    
    # 50 SMA calculation - min_periods=1 keeps it from returning NaN during morning warm-up
    df['sma_50'] = df.groupby('date_only')['Close'].transform(lambda x: x.rolling(window=50, min_periods=1).mean()) 
    df['python_hybrid'] = (df['session_mean'] + df['sma_50']) / 2 

    # Grab the 9:15 AM opening candle of each daily session to define anchor levels
    first_bars = df.groupby('date_only').first() 
    anchors = np.where(first_bars['Close'] > first_bars['Open'], first_bars['High'], first_bars['Low']) 
    anchor_map = pd.Series(anchors, index=first_bars.index) 
    df['anchor'] = df['date_only'].map(anchor_map) 
    
    # Smooth merge phase factor: 0.0 at bar 15 -> 1.0 at bar 45
    df['blend_factor'] = ((df['bar_count'] - 15) / 30.0).clip(0, 1) 
    
    df['ST'] = np.where( 
        df['bar_count'] <= 15, 
        df['anchor'], 
        np.where( 
            df['bar_count'] <= 45, 
            (df['anchor'] * (1 - df['blend_factor'])) + (df['python_hybrid'] * df['blend_factor']), 
            df['python_hybrid'] 
        ) 
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

    # DATA FIX: Keep internal columns intact so downstream modules can reuse them
    # instead of recalculating heavy windows over the continuous data stream
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
            print(f"PXY Error: {e}") 
        return "NONE", 0.0


