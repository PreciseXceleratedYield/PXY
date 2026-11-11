import numpy as np
import pandas as pd

from syscnfgpxy import SYSDTSTPXY_ST1_FACTOR, SYSDTSTPXY_ST1_PERIOD
from sysdthapxy import transform_dtha_ohlc


def _compute_single_st(df: pd.DataFrame, period: float, factor: float) -> tuple:
    """Calculate the main Supertrend line and its absolute mirror line."""
    high = df["High"].to_numpy()
    low = df["Low"].to_numpy()
    close = df["Close"].to_numpy()
    tr1 = high - low
    close_shifted = df["Close"].shift(1).to_numpy(copy=True)
    if len(close_shifted) > 0:
        close_shifted[0] = close[0]
    tr2 = np.abs(high - close_shifted)
    tr3 = np.abs(low - close_shifted)
    tr = np.maximum(tr1, np.maximum(tr2, tr3))
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
    anchor_price = float(hl2[0]) if length > 0 else 0.0

    for i in range(length):
        if i == 0:
            final_upper[i] = basic_upper[i]
            final_lower[i] = basic_lower[i]
            supertrend[i] = final_upper[i]
            st_trend.append("BEAR")
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
        if prev_trend == "BEAR":
            if close[i] > final_upper[i]:
                st_trend.append("BULL")
                supertrend[i] = final_lower[i]
                anchor_price = float(hl2[i])
            else:
                st_trend.append("BEAR")
                supertrend[i] = final_upper[i]
        else:
            if close[i] < final_lower[i]:
                st_trend.append("BEAR")
                supertrend[i] = final_upper[i]
                anchor_price = float(hl2[i])
            else:
                st_trend.append("BULL")
                supertrend[i] = final_lower[i]
        st_distance_from_anchor = supertrend[i] - anchor_price
        mirror_line[i] = anchor_price - st_distance_from_anchor
    return supertrend, mirror_line


def calculate_supertrend(df: pd.DataFrame) -> pd.DataFrame:
    """Add ST, ST Mirror, and the agreed BULL/SIDE/BEAR price classification."""
    if df is None or df.empty:
        return pd.DataFrame() if df is None else df.copy()
    result = transform_dtha_ohlc(df)
    high = pd.to_numeric(result["High"], errors="coerce")
    low = pd.to_numeric(result["Low"], errors="coerce")
    close = pd.to_numeric(result["Close"], errors="coerce")
    close_shifted = close.shift(1)
    if not close_shifted.empty:
        close_shifted.iloc[0] = close.iloc[0]
    true_range = pd.concat(
        [high - low, (high - close_shifted).abs(), (low - close_shifted).abs()],
        axis=1,
    ).max(axis=1)
    atr = true_range.ewm(alpha=1 / SYSDTSTPXY_ST1_PERIOD, adjust=False).mean()
    st_line, mirror_line = _compute_single_st(
        result, period=SYSDTSTPXY_ST1_PERIOD, factor=SYSDTSTPXY_ST1_FACTOR
    )
    result["st_line"] = pd.Series(st_line, index=result.index)
    result["st_mirror"] = pd.Series(mirror_line, index=result.index)
    result["st_atr"] = atr
    highest_bound = np.maximum(result["st_line"], result["st_mirror"])
    lowest_bound = np.minimum(result["st_line"], result["st_mirror"])
    result["ST_Trend"] = np.select(
        [close > highest_bound, close < lowest_bound],
        ["BULL", "BEAR"],
        default="SIDE",
    )
    result["ST"] = result["st_line"]
    result["st1_mirror"] = result["st_mirror"]
    return result


def get_market_trend(df: pd.DataFrame) -> str:
    """Return the latest three-zone classification."""
    if df is None or df.empty or len(df) < 2:
        return "SIDE"
    processed = calculate_supertrend(df)
    if processed.empty:
        return "SIDE"
    return str(processed["ST_Trend"].iloc[-1])
