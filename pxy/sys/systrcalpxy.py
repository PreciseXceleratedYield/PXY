import numpy as np
import pandas as pd


def calculate_wilder_atr(df: pd.DataFrame, period: int) -> pd.Series:
    """Calculate standard true range with Wilder's RMA and SMA seed."""
    if period < 1:
        raise ValueError("ATR period must be a positive integer.")
    if df is None or df.empty:
        return pd.Series(dtype=float, index=getattr(df, "index", None), name="atr")

    columns = {str(column).lower(): column for column in df.columns}
    required = {"high", "low", "close"}
    if not required.issubset(columns):
        raise ValueError("ATR data must include High, Low, and Close columns.")

    high = pd.to_numeric(df[columns["high"]], errors="coerce").astype(float)
    low = pd.to_numeric(df[columns["low"]], errors="coerce").astype(float)
    close = pd.to_numeric(df[columns["close"]], errors="coerce").astype(float)
    previous_close = close.shift(1)
    true_range = pd.concat(
        [
            high - low,
            (high - previous_close).abs(),
            (low - previous_close).abs(),
        ],
        axis=1,
    ).max(axis=1, skipna=True)
    true_range.iloc[0] = (high.iloc[0] - low.iloc[0])

    values = true_range.to_numpy(dtype=float)
    atr = np.full(len(values), np.nan, dtype=float)
    seed_end = period - 1
    if len(values) > seed_end and np.isfinite(values[:period]).all():
        atr[seed_end] = float(np.mean(values[:period]))
        for index in range(period, len(values)):
            if not np.isfinite(values[index]):
                continue
            if np.isfinite(atr[index - 1]):
                atr[index] = (
                    atr[index - 1] * (period - 1) + values[index]
                ) / period

    return pd.Series(atr, index=df.index, name="atr")


def _compute_single_st(
    df: pd.DataFrame, factor: float, atr_period: int
) -> tuple:
    """Compute mirrored Supertrend bands using standard Wilder ATR."""
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

    atr = calculate_wilder_atr(df, atr_period).to_numpy(dtype=float)

    basic_upper = src + (factor * atr)
    basic_lower = src - (factor * atr)

    final_upper = np.full(length, np.nan)
    final_lower = np.full(length, np.nan)
    supertrend = np.full(length, np.nan)
    mirror_line = np.full(length, np.nan)
    st_trend = np.full(length, np.nan)
    first_valid = np.flatnonzero(np.isfinite(atr))
    if not len(first_valid):
        return tuple(
            pd.Series(values, index=df.index)
            for values in (supertrend, mirror_line, m0, st_trend)
        )
    start = int(first_valid[0])
    anchor_price = float(src[start])

    for i in range(start, length):
        if i == start:
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
