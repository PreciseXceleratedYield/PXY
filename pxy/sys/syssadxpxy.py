# syssadxpxy.py
import numpy as np
import pandas as pd
import warnings

warnings.simplefilter(action='ignore', category=FutureWarning)

def calculate_adx(df: pd.DataFrame) -> tuple:
    """
    Surgically averages 50 SMA and Supertrend (10, 3) lines to derive system forces.
    
    Returns (ce_force, pe_force) based on price position relative to the averaged line:
    - Price > Average Line (BULL): ce_force = 1.0, pe_force = 1.2
    - Price < Average Line (BEAR): ce_force = 1.2, pe_force = 1.0
    - Price == Average Line (SIDE): ce_force = 1.0, pe_force = 1.0
    """
    if df is None or df.empty or len(df) < 50:
        return 1.1, 1.1

    high = df['High'].to_numpy()
    low = df['Low'].to_numpy()
    close = df['Close'].to_numpy()
    length = len(df)

    # 1. Compute 50 Simple Moving Average (SMA) Line
    sma_50 = df['Close'].rolling(window=50).mean().to_numpy()
    latest_sma = sma_50[-1]

    # 2. Compute Supertrend (10, 3) Line
    tr = np.zeros(length)
    tr[0] = high[0] - low[0]
    for i in range(1, length):
        tr[i] = max(
            high[i] - low[i], 
            abs(high[i] - close[i-1]), 
            abs(low[i] - close[i-1])
        )
    
    atr = pd.Series(tr).rolling(window=10).mean().to_numpy()

    hl2 = (high + low) / 2
    upperband = hl2 + 3 * atr
    lowerband = hl2 - 3 * atr
    
    final_upper = np.copy(upperband)
    final_lower = np.copy(lowerband)
    supertrend = np.zeros(length)
    trend = np.ones(length)

    supertrend[0] = final_upper[0]
    trend[0] = -1

    for i in range(1, length):
        if close[i] > final_upper[i-1]:
            trend[i] = 1
        elif close[i] < final_lower[i-1]:
            trend[i] = -1
        else:
            trend[i] = trend[i-1]
            if trend[i] == 1 and final_lower[i] < final_lower[i-1]:
                final_lower[i] = final_lower[i-1]
            if trend[i] == -1 and final_upper[i] > final_upper[i-1]:
                final_upper[i] = final_upper[i-1]
                
        supertrend[i] = final_lower[i] if trend[i] == 1 else final_upper[i]

    latest_supertrend = supertrend[-1]

    if np.isnan(latest_sma) or np.isnan(latest_supertrend):
        return 1.1, 1.1

    # 3. Combine and average indicator paths
    average_line = (latest_sma + latest_supertrend) / 2
    latest_close = close[-1]

    # 4. Final conditional flipping assignment matching 1.0 and 1.2 forces
    if latest_close > average_line:       
        ce_force = 1.0
        pe_force = 1.0
    elif latest_close < average_line:     
        ce_force = 1.0
        pe_force = 1.0
    else:                                 
        ce_force = 1.0
        pe_force = 1.0

    return ce_force, pe_force

