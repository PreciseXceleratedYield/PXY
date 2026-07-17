# pxy_engine.py
import pandas as pd
import numpy as np
from sysdtafpxy import fetch_yf_data

def get_pxy_data(tickerSymbol=None, df=None):
    if df is None:
        df = fetch_yf_data()
        
    if df is None or df.empty:
        return None, None, None, pd.DataFrame()
        
    # Safeguard: Separate processing safely from global reference memory
    df = df.copy()
    
    required_cols = ['Open', 'High', 'Low', 'Close']
    for col in required_cols:
        if col not in df.columns:
            return None, None, None, pd.DataFrame()

    # ==================================================
    # 🕯️ NEW CUSTOM CANDLE TRANSFORM (LAST OHLC/4 OPEN)
    # ==================================================
    custom_df = pd.DataFrame(index=df.index)
    
    # 1. Current Close is exactly the original market close
    custom_df['Close'] = df['Close']

    # 2. Current Open is exactly the previous candle's full OHLC average (OHLC / 4)
    # Calculate the raw OHLC/4 for every row first
    raw_ohlc_4 = (df['Open'] + df['High'] + df['Low'] + df['Close']) / 4
    
    # Shift it forward by 1 bar so last candle's OHLC/4 becomes the current candle's Open
    custom_df['Open'] = raw_ohlc_4.shift(1)
    
    # Seed the very first row safely to avoid a NaN starting point
    custom_df.iloc[0, custom_df.columns.get_loc('Open')] = raw_ohlc_4.iloc[0]

    # 3. High and Low bound logically to the new open/close matrix
    custom_df['High'] = np.maximum(df['High'].values, np.maximum(custom_df['Open'].values, custom_df['Close'].values))
    custom_df['Low'] = np.minimum(df['Low'].values, np.minimum(custom_df['Open'].values, custom_df['Close'].values))

    # ==================================================
    # 🎨 COLOR PROCESSING (CUSTOM CLOSE VS CUSTOM OPEN)
    # ==================================================
    # Green when Custom Close is above or equal to Custom Open; otherwise Red
    is_green = custom_df['Close'] >= custom_df['Open']
    custom_df["pxy_color"] = np.select([is_green], ["green"], default="red")

    # ==================================================
    # 🛡️ PRODUCTION OUTPUT FILTER (SAME SIGNATURE PASSTHROUGH)
    # ==================================================
    final_df = custom_df.copy()
    pxy_close = final_df['Close'].copy()  # Delivers Custom Close Series (Original Close)
    pxy_open = final_df['Open'].copy()    # Delivers Custom Open Series (Last OHLC/4)
    pxy_color_series = final_df['pxy_color'].copy()
    
    return pxy_close, pxy_open, pxy_color_series, final_df




