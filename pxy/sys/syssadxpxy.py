#!/usr/bin/env python3
# syssadxpxy.py
import numpy as np
import pandas as pd
import warnings
from syscnfgpxy import (
    SYSSADXPXY_MA_PERIOD,
    SYSSADXPXY_SUPERTREND_FACTOR,
    SYSSADXPXY_SUPERTREND_PERIOD,
    SYSSADXPXY_USE_TSMA,
)

warnings.simplefilter(action='ignore', category=FutureWarning)

# 🎛️ HARD-CODED OPERATIONAL LOGIC SWITCH
# Set True  -> Uses 50-period Time Series Moving Average (TSMA)
# Set False -> Uses 50-period Simple Moving Average (SMA)
USE_TSMA = SYSSADXPXY_USE_TSMA

def _calculate_tsma_50_line(close_series: pd.Series) -> np.ndarray:
    """
    Vectorized 50-period Time Series Moving Average (TSMA) engine.
    Applies linear regression curve fitting over a rolling 50-window slice.
    Formula: TSMA = 3 * WMA(50) - 2 * SMA(50)
    """
    length = len(close_series)
    if length < SYSSADXPXY_MA_PERIOD:
        return close_series.rolling(window=length, min_periods=1).mean().to_numpy()

    # 1. Standard 50 SMA Component
    sma = close_series.rolling(window=SYSSADXPXY_MA_PERIOD).mean()

    # 2. Linear Weighted Moving Average (WMA) 50 Component
    weights = np.arange(1, SYSSADXPXY_MA_PERIOD + 1)
    wma = close_series.rolling(window=SYSSADXPXY_MA_PERIOD).apply(
        lambda x: np.dot(x, weights) / weights.sum(), 
        raw=True
    )

    # 3. TSMA Endpoint Curve Fitting Intersection
    tsma = (3 * wma) - (2 * sma)
    return tsma.to_numpy()

def calculate_adx(df: pd.DataFrame) -> tuple:
    """
    Surgically averages a 50-period moving line (SMA or TSMA) with Supertrend (10, 3) 
    to derive clean system baseline forces.
    
    Returns (ce_force, pe_force) based on price position relative to the averaged line:
    - Price > Average Line (BULL): ce_force = 1.0, pe_force = 1.2
    - Price < Average Line (BEAR): ce_force = 1.2, pe_force = 1.0
    - Price == Average Line (SIDE): ce_force = 1.0, pe_force = 1.0
    """
    if df is None or df.empty or len(df) < SYSSADXPXY_MA_PERIOD:
        return 1.1, 1.1

    high = df['High'].to_numpy()
    low = df['Low'].to_numpy()
    close = df['Close'].to_numpy()
    length = len(df)

    # 1. Hard-Coded Switch Logic Resolution
    if SYSSADXPXY_USE_TSMA:
        # High-performance rolling TSMA 50 engine calculation path
        moving_line = _calculate_tsma_50_line(df['Close'])
    else:
        # Standard fallback to original Simple Moving Average path
        moving_line = df['Close'].rolling(window=SYSSADXPXY_MA_PERIOD).mean().to_numpy()
        
    latest_moving_val = moving_line[-1]

    # 2. Compute Supertrend (10, 3) Line
    tr = np.zeros(length)
    tr[0] = high[0] - low[0]
    for i in range(1, length):
        tr[i] = max(
            high[i] - low[i], 
            abs(high[i] - close[i-1]), 
            abs(low[i] - close[i-1])
        )
    
    atr = pd.Series(tr).rolling(window=SYSSADXPXY_SUPERTREND_PERIOD).mean().to_numpy()

    hl2 = (high + low) / 2
    upperband = hl2 + SYSSADXPXY_SUPERTREND_FACTOR * atr
    lowerband = hl2 - SYSSADXPXY_SUPERTREND_FACTOR * atr
    
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

    if np.isnan(latest_moving_val) or np.isnan(latest_supertrend):
        return 1.1, 1.1

    # 3. Combine and average indicator paths
    average_line = (latest_moving_val + latest_supertrend) / 2
    latest_close = close[-1]

    # 4. Final conditional flipping assignment matching forces 
    if latest_close > average_line:       
        ce_force = 1.0
        pe_force = 1.2
    elif latest_close < average_line:     
        ce_force = 1.2
        pe_force = 1.0
    else:                                 
        ce_force = 1.0
        pe_force = 1.0

    return ce_force, pe_force
