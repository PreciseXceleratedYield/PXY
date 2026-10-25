
import numpy as np
import pandas as pd
from syscnfgpxy import (
    SYSDTSTPXY_ST1_FACTOR,
    SYSDTSTPXY_ST1_PERIOD,
)


# ==============================================================================
# MASTER CONFIGURATION LAYER
# ==============================================================================
def _compute_single_st(df: pd.DataFrame, period: float, factor: float) -> tuple:
    """Calculate fixed active ST and dormant mirror levels, switching on price crosses."""
    high = df["High"].to_numpy()
    low = df["Low"].to_numpy()
    close = df["Close"].to_numpy()

    length = len(df)
    supertrend = np.zeros(length)
    mirror_line = np.zeros(length)

    if length == 0:
        return supertrend, mirror_line

    close_shifted = df["Close"].shift(1).to_numpy(copy=True)
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

    # Initialize the active ST and its dormant mirror.
    anchor_price = float(hl2[0])
    active_st = float(hl2[0] + factor * atr[0])
    dormant_mirror = (2.0 * anchor_price) - active_st

    supertrend[0] = active_st
    mirror_line[0] = dormant_mirror

    for i in range(1, length):
        previous_close = float(close[i - 1])
        current_close = float(close[i])

        # Detect a crossing of the dormant mirror in either direction.
        crossed_mirror = (
            (
                previous_close <= dormant_mirror
                and current_close > dormant_mirror
            )
            or
            (
                previous_close >= dormant_mirror
                and current_close < dormant_mirror
            )
        )

        if crossed_mirror:
            # The crossed dormant mirror becomes the active ST.
            active_st = dormant_mirror

            # Reset the anchor and establish the next dormant mirror.
            anchor_price = float(hl2[i])
            dormant_mirror = (2.0 * anchor_price) - active_st

        # Hold both levels constant until the next crossing.
        supertrend[i] = active_st
        mirror_line[i] = dormant_mirror

    return supertrend, mirror_line


def get_market_trend(df: pd.DataFrame) -> str:
    """
    Evaluate the latest candle using the three-zone market classifier.

    Returns:
        'BULL', 'BEAR', or 'SIDE'.
    """
    if df is None or df.empty or len(df) < 2:
        return "SIDE"

    st1_line, st1_mirror = _compute_single_st(
        df,
        period=SYSDTSTPXY_ST1_PERIOD,
        factor=SYSDTSTPXY_ST1_FACTOR,
    )

    close_curr = float(df["Close"].iloc[-1])
    st_curr = float(st1_line[-1])
    mirror_curr = float(st1_mirror[-1])

    highest_bound = max(st_curr, mirror_curr)
    lowest_bound = min(st_curr, mirror_curr)

    if close_curr > highest_bound:
        return "BULL"
    elif close_curr < lowest_bound:
        return "BEAR"

    return "SIDE"


def calculate_supertrend(df: pd.DataFrame) -> pd.DataFrame:
    """Add the configured Supertrend fields used by entry routing."""
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
        adjust=False,
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
