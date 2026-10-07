import numpy as np
import pandas as pd


def _compute_single_st(
    df: pd.DataFrame, factor: float, atr_value: float
) -> tuple:
    """Helper to compute PXY Supertrend bands and the mirror line."""
    high = df["High"].to_numpy()
    low = df["Low"].to_numpy()
    open_arr = df["Open"].to_numpy()
    close = df["Close"].to_numpy()

    length = len(df)
    if length == 0:
        return (
            pd.Series(dtype=float),
            pd.Series(dtype=float),
            pd.Series(dtype=float),
            pd.Series(dtype=int),
        )

    m0 = np.where(close >= open_arr, (close + high) / 2.0, (close + low) / 2.0)
    src = (high + low) / 2.0

    atr = np.full(length, atr_value)

    basic_upper = src + (factor * atr)
    basic_lower = src - (factor * atr)

    final_upper = np.zeros(length)
    final_lower = np.zeros(length)
    supertrend = np.zeros(length)
    mirror_line = np.zeros(length)
    st_trend = np.ones(length)

    anchor_price = float(src[0])

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
        st_line = final_lower[i] if current_trend == 1 else final_upper[i]
        supertrend[i] = st_line

        st_distance_from_anchor = st_line - anchor_price
        mirror_line[i] = anchor_price - st_distance_from_anchor

    return (
        pd.Series(supertrend, index=df.index),
        pd.Series(mirror_line, index=df.index),
        pd.Series(m0, index=df.index),
        pd.Series(st_trend, index=df.index),
    )

