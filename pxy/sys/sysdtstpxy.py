import numpy as np
import pandas as pd
from syscnfgpxy import (
    SYSDTSTPXY_ST1_FACTOR,
    SYSDTSTPXY_ST1_PERIOD,
)

# ==============================================================================
# 🎛️ MASTER CONFIGURATION LAYER
# ==============================================================================
def _compute_single_st(df: pd.DataFrame, period: float, factor: float) -> tuple:
    """Computes basic Supertrend bands and its exact absolute inverse mirror line."""
    high = df['High'].to_numpy()
    low = df['Low'].to_numpy()
    close = df['Close'].to_numpy()

    tr1 = high - low
    # FIX: Properly shift the close array to capture historical gaps
    close_shifted = df['Close'].shift(1).to_numpy()
    if len(close_shifted) > 0:
        close_shifted[0] = close[0]

    tr2 = np.abs(high - close_shifted)
    tr3 = np.abs(low - close_shifted)
    tr = np.maximum(tr1, np.maximum(tr2, tr3))
    
    # Calculate exponential moving average for true range
    atr = pd.Series(tr, index=df.index).ewm(alpha=1 / period, adjust=False).mean().to_numpy()

    hl2 = (high + low) / 2
    basic_upper = hl2 + (factor * atr)
    basic_lower = hl2 - (factor * atr)

    length = len(df)
    final_upper = np.zeros(length)
    final_lower = np.zeros(length)
    supertrend = np.zeros(length)
    mirror_line = np.zeros(length)
    st_trend = []

    # FIX: Extract the first scalar value instead of copying the whole array
    anchor_price = float(hl2[0]) if length > 0 else 0.0

    for i in range(length):
        if i == 0:
            final_upper[i] = basic_upper[i]
            final_lower[i] = basic_lower[i]
            supertrend[i] = final_upper[i]
            st_trend.append('BEAR')
            mirror_line[i] = anchor_price - (supertrend[i] - anchor_price)
            continue

        prev_upper = final_upper[i - 1]
        prev_lower = final_lower[i - 1]
        prev_trend = st_trend[i - 1]

        if basic_upper[i] < prev_upper or close[i - 1] > prev_upper:
            final_upper[i] = basic_upper[i]
        else:
            final_upper[i] = prev_upper

        if basic_lower[i] > prev_lower or close[i - 1] < prev_lower:
            final_lower[i] = basic_lower[i]
        else:
            final_lower[i] = prev_lower

        if prev_trend == 'BEAR':
            if close[i] > final_upper[i]:
                st_trend.append('BULL')
                supertrend[i] = final_lower[i]
                anchor_price = float(hl2[i])
            else:
                st_trend.append('BEAR')
                supertrend[i] = final_upper[i]
        else:
            if close[i] < final_lower[i]:
                st_trend.append('BEAR')
                supertrend[i] = final_upper[i]
                anchor_price = float(hl2[i])
            else:
                st_trend.append('BULL')
                supertrend[i] = final_lower[i]

        st_distance_from_anchor = supertrend[i] - anchor_price
        mirror_line[i] = anchor_price - st_distance_from_anchor

    return supertrend, mirror_line

def get_market_trend(df: pd.DataFrame) -> str:
    """
    Evaluates the data frame using a 3-Zone Market Classifier.
    Returns: 'BULL', 'BEAR', or 'SIDE' based on the latest candle.
    """
    if df is None or df.empty or len(df) < 2:
        return 'SIDE'

    st1_line, st1_mirror = _compute_single_st(
        df, period=SYSDTSTPXY_ST1_PERIOD, factor=SYSDTSTPXY_ST1_FACTOR
    )
    
    close_curr = float(df['Close'].iloc[-1])
    st_curr = float(st1_line[-1])
    mirror_curr = float(st1_mirror[-1])
    
    highest_bound = max(st_curr, mirror_curr)
    lowest_bound = min(st_curr, mirror_curr)
    
    if close_curr > highest_bound:
        return 'BULL'
    elif close_curr < lowest_bound:
        return 'BEAR'
    else:
        return 'SIDE'
