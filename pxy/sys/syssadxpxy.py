# syssadxpxy.py
import numpy as np
import pandas as pd
import warnings

warnings.simplefilter(action='ignore', category=FutureWarning)

def calculate_adx(df: pd.DataFrame) -> tuple:
    """
    Surgically averages 50 SMA and Supertrend (10, 3) lines to derive system forces.
    
    Returns (ce_force, pe_force) based on price position relative to the averaged line:
    - Price > Average Line:  ce_force = 1.0, pe_force = 1.4
    - Price < Average Line:  ce_force = 1.4, pe_force = 1.0
    - Price == Average Line: ce_force = 1.0, pe_force = 1.0
    """
    # Strict fallback check: Requires minimum 50 rows to initialize 50 SMA
    if df is None or df.empty or len(df) < 50:
        return 1.5, 1.5

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
    
    # 10-period standard ATR
    atr = pd.Series(tr).rolling(window=10).mean().to_numpy()

    hl2 = (high + low) / 2
    upperband = hl2 + 3 * atr
    lowerband = hl2 - 3 * atr
    
    final_upper = np.copy(upperband)
    final_lower = np.copy(lowerband)
    supertrend = np.zeros(length)
    trend = np.ones(length)  # 1 = Up trend, -1 = Down trend

    # Strict loop to track trailing stop bands (TradingView/PineScript Standard)
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

    # Verification fallback check if indicators fail or generate NaNs
    if np.isnan(latest_sma) or np.isnan(latest_supertrend):
        return 1.5, 1.5

    # 3. Combine and average indicator paths
    average_line = (latest_sma + latest_supertrend) / 2
    latest_close = close[-1]

    # 4. Final conditional flipping assignment
    if latest_close > average_line:       # Price is ABOVE the combined line
        ce_force = 1.0
        pe_force = 2.0
    elif latest_close < average_line:     # Price is BELOW the combined line
        ce_force = 2.0
        pe_force = 1.0
    else:                                 # Price is EXACTLY EQUAL to the line
        ce_force = 1.0
        pe_force = 1.0

    return ce_force, pe_force

