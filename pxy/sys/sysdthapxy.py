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
    # 🎨 COLOR PROCESSING (STRAIGHT 0c/2 MODE FROM DATAFRAME)
    # ==================================================
    is_green = df['Close'] >= df['Open']
    
    conditions = [is_green]
    choices = ["green"]
    df["pxy_color"] = np.select(conditions, choices, default="red")

    # ==================================================
    # 🛡️ PRODUCTION OUTPUT FILTER (FORCED LIVE RUNNING)
    # ==================================================
    final_df = df.copy()
    
    pxy_close = final_df['Close'].copy()
    pxy_open = final_df['Open'].copy()
    pxy_color_series = final_df['pxy_color'].copy()

    return pxy_close, pxy_open, pxy_color_series, final_df



