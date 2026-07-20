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

    # Extract raw values as numpy arrays for speed
    raw_open = df['Open'].values
    raw_high = df['High'].values
    raw_low = df['Low'].values
    raw_close = df['Close'].values
    
    n = len(df)
    ha_open = np.zeros(n)
    ha_close = np.zeros(n)

    # 1. Calculate Pure HA Close first (Average of current OHLC)
    ha_close = (raw_open + raw_high + raw_low + raw_close) / 4.0

    # 2. Calculate Pure HA Open recursively
    # Seed the very first row using standard market open/close average
    ha_open[0] = (raw_open[0] + raw_close[0]) / 2.0
    
    # Process the recursive chain safely via a fast numpy loop
    for i in range(1, n):
        ha_open[i] = (ha_open[i-1] + ha_close[i-1]) / 2.0

    # 3. Calculate Pure HA High and Low
    ha_high = np.maximum(raw_high, np.maximum(ha_open, ha_close))
    ha_low = np.minimum(raw_low, np.minimum(ha_open, ha_close))

    # ==================================================
    # 🕯️ BUILD CUSTOM DATAFRAME
    # ==================================================
    custom_df = pd.DataFrame(index=df.index)
    custom_df['Open'] = ha_open
    custom_df['High'] = ha_high
    custom_df['Low'] = ha_low
    custom_df['Close'] = ha_close

    # ==================================================
    # 🎨 COLOR PROCESSING (PURE HA CLOSE VS PURE HA OPEN)
    # ==================================================
    is_green = custom_df['Close'] >= custom_df['Open']
    custom_df["pxy_color"] = np.select([is_green], ["green"], default="red")

    # ==================================================
    # 🛡️ PRODUCTION OUTPUT FILTER (SAME SIGNATURE PASSTHROUGH)
    # ==================================================
    final_df = custom_df.copy()
    pxy_close = final_df['Close'].copy()  
    pxy_open = final_df['Open'].copy()    
    pxy_color_series = final_df['pxy_color'].copy()
    
    return pxy_close, pxy_open, pxy_color_series, final_df
