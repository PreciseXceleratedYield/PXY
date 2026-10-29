
import numpy as np
import pandas as pd
from syscnfgpxy import (
    SYSDTSTPXY_ST1_FACTOR,
    SYSDTSTPXY_ST1_PERIOD,
)


# ==============================================================================
# MASTER CONFIGURATION LAYER
# ==============================================================================
def _compute_single_st(
    df: pd.DataFrame,
    period: float,
    factor: float
) -> tuple:
    """Calculate the original Supertrend and a price-following mirror line."""

    high = df['High'].to_numpy()
    low = df['Low'].to_numpy()
    close = df['Close'].to_numpy()

    if len(df) == 0:
        return np.array([]), np.array([])

    # Calculate true range, preserving the original logic.
    close_shifted = df['Close'].shift(1).to_numpy(copy=True)
    close_shifted[0] = close[0]

    tr1 = high - low
    tr2 = np.abs(high - close_shifted)
    tr3 = np.abs(low - close_shifted)
    tr = np.maximum(tr1, np.maximum(tr2, tr3))

    atr = (
        pd.Series(tr, index=df.index)
        .ewm(alpha=1 / period, adjust=False)
        .mean()
        .to_numpy()
    )

    hl2 = (high + low) / 2
    basic_upper = hl2 + (factor * atr)
    basic_lower = hl2 - (factor * atr)

    length = len(df)
    final_upper = np.zeros(length)
    final_lower = np.zeros(length)
    supertrend = np.zeros(length)
    mirror_line = np.zeros(length)
    st_trend = []

    # Preserve the original first-candle ST and mirror calculations.
    anchor_price = float(hl2[0])

    for i in range(length):
        if i == 0:
            final_upper[i] = basic_upper[i]
            final_lower[i] = basic_lower[i]
            supertrend[i] = final_upper[i]
            st_trend.append('BEAR')
            mirror_line[i] = (
                anchor_price - (supertrend[i] - anchor_price)
            )
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

        # Original Supertrend direction and line calculation: unchanged.
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

    # Mirror calculation:
    # Keep the first candle's signed point offset from price constant.
    initial_mirror_offset = mirror_line[0] - close[0]
    mirror_line[:] = close + initial_mirror_offset

    return supertrend, mirror_line


def get_market_trend(df: pd.DataFrame) -> str:
    """
    Evaluate the latest candle using the Supertrend and mirror boundaries.
    Returns 'BULL', 'BEAR', or 'SIDE'.
    """
    if df is None or df.empty or len(df) < 2:
        return 'SIDE'

    st1_line, st1_mirror = _compute_single_st(
        df,
        period=SYSDTSTPXY_ST1_PERIOD,
        factor=SYSDTSTPXY_ST1_FACTOR
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


def calculate_supertrend(df: pd.DataFrame) -> pd.DataFrame:
    """Add configured Supertrend fields using the shared calculation."""
    if df is None or df.empty:
        return pd.DataFrame() if df is None else df.copy()

    result = df.copy()

    high = pd.to_numeric(result["High"], errors="coerce")
    low = pd.to_numeric(result["Low"], errors="coerce")
    close = pd.to_numeric(result["Close"], errors="coerce")

    close_shifted = close.shift(1)
    if not close_shifted.empty:
        close_shifted.iloc[0] = close.iloc[0]

    true_range = pd.concat(
        [
            high - low,
            (high - close_shifted).abs(),
            (low - close_shifted).abs(),
        ],
        axis=1,
    ).max(axis=1)

    atr = true_range.ewm(
        alpha=1 / SYSDTSTPXY_ST1_PERIOD,
        adjust=False
    ).mean()

    st_line, mirror_line = _compute_single_st(
        result,
        period=SYSDTSTPXY_ST1_PERIOD,
        factor=SYSDTSTPXY_ST1_FACTOR,
    )

    result["st_line"] = pd.Series(st_line, index=result.index)
    result["st_mirror"] = pd.Series(mirror_line, index=result.index)
    result["st_atr"] = atr

    result["ST_Trend"] = np.select(
        [
            close > np.maximum(result["st_line"], result["st_mirror"]),
            close < np.minimum(result["st_line"], result["st_mirror"]),
        ],
        ["BULL", "BEAR"],
        default="SIDE",
    )

    return result
