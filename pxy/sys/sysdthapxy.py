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
    # 🕯️ PURE HEIKIN-ASHI TRANSFORM (SYNTHETIC ONLY)
    # ==================================================
    ha_df = pd.DataFrame(index=df.index)
    
    # 1. HA Close is the average of standard Open, High, Low, and Close
    ha_df['Close'] = (df['Open'] + df['High'] + df['Low'] + df['Close']) / 4

    # 2. HA Open is the average of the prior HA Open and prior HA Close
    ha_open = np.zeros(len(df))
    ha_open[0] = df['Open'].iloc[0]  # Explicitly seeds the very first candle
    
    close_vals = ha_df['Close'].values
    for i in range(1, len(df)):
        ha_open[i] = (ha_open[i-1] + close_vals[i-1]) / 2
        
    ha_df['Open'] = ha_open

    # 3. HA High and Low pick the absolute extremes out of market and HA values
    ha_df['High'] = np.maximum(df['High'].values, np.maximum(ha_df['Open'].values, ha_df['Close'].values))
    ha_df['Low'] = np.minimum(df['Low'].values, np.minimum(ha_df['Open'].values, ha_df['Close'].values))

    # ==================================================
    # 🎨 COLOR PROCESSING (HA CLOSE VS HA OPEN)
    # ==================================================
    # Green when HA Close is above or equal to HA Open; otherwise Red
    is_green = ha_df['Close'] >= ha_df['Open']
    ha_df["pxy_color"] = np.select([is_green], ["green"], default="red")

    # ==================================================
    # 🛡️ PRODUCTION OUTPUT FILTER (PURE HA PASSTHROUGH)
    # ==================================================
    final_df = ha_df.copy()
    pxy_close = final_df['Close'].copy()  # Delivers pure HA Close Series
    pxy_open = final_df['Open'].copy()    # Delivers pure HA Open Series
    pxy_color_series = final_df['pxy_color'].copy()
    
    return pxy_close, pxy_open, pxy_color_series, final_df



