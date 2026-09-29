# systrcalpxy.py
import numpy as np
import pandas as pd

def _compute_single_st(df: pd.DataFrame, period: float, factor: float) -> tuple:
    """Helper to compute PXY Supertrend bands and the mirror line."""
    high = df['High'].to_numpy()
    low = df['Low'].to_numpy()
    open_arr = df['Open'].to_numpy()
    close = df['Close'].to_numpy()

    length = len(df)
    if length == 0:
        return pd.Series(dtype=float), pd.Series(dtype=float), pd.Series(dtype=float), pd.Series(dtype=int)

    m0 = np.where(close >= open_arr, (close + high) / 2.0, (close + low) / 2.0)
    src = (high + low) / 2.0  
    
    from syskatrpxy import calculate_atr
    atr = calculate_atr(df).to_numpy()

    basic_upper = src + (factor * atr)
    basic_lower = src - (factor * atr)

    final_upper = np.zeros(length)
    final_lower = np.zeros(length)
    supertrend = np.zeros(length)
    mirror_line = np.zeros(length)
    st_trend = np.ones(length)  

    # 🛠️ FIXED: Extract the first scalar element instead of trying to cast the entire array
    anchor_price = float(src[0]) if length > 0 else 0.0

    for i in range(length):
        if i == 0:
            final_upper[i] = basic_upper[i]
            final_lower[i] = basic_lower[i]
            supertrend[i] = final_upper[i]
            st_trend[i] = -1 
            mirror_line[i] = anchor_price - (supertrend[i] - anchor_price)
            continue

        prev_upper = final_upper[i - 1]
        prev_lower = final_lower[i - 1]
        prev_trend = st_trend[i - 1]

        if src[i] < prev_upper:
            final_upper[i] = min(basic_upper[i], prev_upper)
        else:
            final_upper[i] = basic_upper[i]

        if src[i] > prev_lower:
            final_lower[i] = max(basic_lower[i], prev_lower)
        else:
            final_lower[i] = basic_lower[i]

        if prev_trend == -1 and m0[i] > prev_upper:  
            current_trend = 1
            anchor_price = float(src[i])
        elif prev_trend == 1 and m0[i] < prev_lower:  
            current_trend = -1
            anchor_price = float(src[i])
        else:
            current_trend = prev_trend

        st_trend[i] = current_trend
        stLine = final_lower[i] if current_trend == 1 else final_upper[i]
        supertrend[i] = stLine

        st_distance_from_anchor = stLine - anchor_price
        mirror_line[i] = anchor_price - st_distance_from_anchor

    return (pd.Series(supertrend, index=df.index), 
            pd.Series(mirror_line, index=df.index), 
            pd.Series(m0, index=df.index), 
            pd.Series(st_trend, index=df.index))


def _compute_sma_trend(df: pd.DataFrame, period: int) -> tuple:
    """Processes pure Simple Moving Average trend vectors."""
    sma_series = df['Close'].rolling(window=period, min_periods=1).mean()
    trend_series = np.where(df['Close'] >= sma_series, 'BULL', 'BEAR')
    return sma_series, pd.Series(trend_series, index=df.index)


def _compute_combo_force(df: pd.DataFrame, st_period: int, st_factor: float, sma_period: int) -> tuple:
    """Processes exact parity mathematical line for configurable Supertrend + SMA."""
    high = df['High'].to_numpy()
    low = df['Low'].to_numpy()
    close = df['Close'].to_numpy()
    length = len(df)
    
    sma_values = df['Close'].rolling(window=sma_period).mean().to_numpy()

    tr = np.zeros(length)
    tr = high - low
    for i in range(1, length):
        tr[i] = max(high[i] - low[i], abs(high[i] - close[i-1]), abs(low[i] - close[i-1]))
    
    atr_values = pd.Series(tr).rolling(window=st_period).mean().to_numpy()
    hl2 = (high + low) / 2
    final_upper = hl2 + st_factor * atr_values
    final_lower = hl2 - st_factor * atr_values
    
    supertrend_path = np.copy(final_upper)
    trend_path = np.ones(length) * -1

    for i in range(1, length):
        if close[i] > final_upper[i-1]: 
            trend_path[i] = 1
        elif close[i] < final_lower[i-1]: 
            trend_path[i] = -1
        else:
            trend_path[i] = trend_path[i-1]
            if trend_path[i] == 1 and final_lower[i] < final_lower[i-1]: 
                final_lower[i] = final_lower[i-1]
            if trend_path[i] == -1 and final_upper[i] > final_upper[i-1]: 
                final_upper[i] = final_upper[i-1]
        supertrend_path[i] = final_lower[i] if trend_path[i] == 1 else final_upper[i]

    comb_average_line = (sma_values + supertrend_path) / 2
    st_trend_series = np.where(close > comb_average_line, 'BULL', np.where(close < comb_average_line, 'BEAR', 'SIDE'))
    
    return pd.Series(comb_average_line, index=df.index), pd.Series(st_trend_series, index=df.index)

