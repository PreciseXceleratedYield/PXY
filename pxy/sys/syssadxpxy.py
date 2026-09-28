# syssadxpxy.py
import numpy as np
import pandas as pd
import warnings

warnings.simplefilter(action='ignore', category=FutureWarning)

def calculate_adx(df: pd.DataFrame) -> tuple:
    """
    Simplified trend force calculator using a 50-period SMA.
    
    Returns (ce_force, pe_force) based on price position relative to 50 SMA:
    - Price > SMA (Above): ce_force = 1.0, pe_force = 1.234
    - Price < SMA (Below): ce_force = 1.234, pe_force = 1.0
    - Price == SMA (Equal): ce_force = 1.0, pe_force = 1.0
    """
    # Requires minimum 50 rows to calculate a 50 SMA
    if df is None or df.empty or len(df) < 50:
        return 1.5, 1.5

    close_series = df['Close']
    sma_50 = close_series.rolling(window=50).mean().to_numpy()
    
    latest_close = close_series.iloc[-1]
    latest_sma = sma_50[-1]

    # Handle edge case where SMA data is missing
    if np.isnan(latest_sma):
        return 1.5, 1.5

    # 🔄 Strict Position Logic (Equal = 1.0)
    if latest_close > latest_sma:       # Price is ABOVE 50 SMA
        ce_force = 1.0
        pe_force = 1.234
    elif latest_close < latest_sma:     # Price is BELOW 50 SMA
        ce_force = 1.234
        pe_force = 1.0
    else:                               # Price is EXACTLY EQUAL to 50 SMA
        ce_force = 1.0
        pe_force = 1.0

    return ce_force, pe_force

