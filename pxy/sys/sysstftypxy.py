"""ST50: average of TradingView Supertrend(3,3) and SMA(50)."""
import numpy as np
import pandas as pd


def calculate_st50(df: pd.DataFrame) -> pd.DataFrame:
    """Use supplied DTHA-transformed candles; do not transform or refetch."""
    result = df.copy()
    result["st50"] = np.nan
    result["ST50_Trend"] = "NA"
    if len(result) < 50:
        return result

    high = pd.to_numeric(result["High"], errors="coerce")
    low = pd.to_numeric(result["Low"], errors="coerce")
    close = pd.to_numeric(result["Close"], errors="coerce")
    if not np.isfinite(pd.concat([high, low, close], axis=1).to_numpy()).all():
        return result

    previous = close.shift(1)
    tr = pd.concat([high - low, (high - previous).abs(),
                    (low - previous).abs()], axis=1).max(axis=1)
    atr = np.full(len(result), np.nan)
    atr[2] = tr.iloc[:3].mean()
    for i in range(3, len(result)):
        atr[i] = (atr[i - 1] * 2 + tr.iloc[i]) / 3

    hl2 = (high + low).to_numpy() / 2
    basic_upper = hl2 + 3.0 * atr
    basic_lower = hl2 - 3.0 * atr
    closes = close.to_numpy()
    st = np.full(len(result), np.nan)
    upper = basic_upper[2]
    lower = basic_lower[2]
    bullish = False  # TradingView starts on the upper band.
    st[2] = upper

    for i in range(3, len(result)):
        prev_upper, prev_lower = upper, lower
        upper = (basic_upper[i] if basic_upper[i] < prev_upper
                 or closes[i - 1] > prev_upper else prev_upper)
        lower = (basic_lower[i] if basic_lower[i] > prev_lower
                 or closes[i - 1] < prev_lower else prev_lower)
        if bullish:
            bullish = not (closes[i] < lower)
        else:
            bullish = closes[i] > upper
        st[i] = lower if bullish else upper

    sma50 = close.rolling(50, min_periods=50).mean().to_numpy()
    combined = (st + sma50) / 2
    result["st50"] = combined
    trend = np.where(closes > combined, "BULL",
                     np.where(closes < combined, "BEAR", None))
    result["ST50_Trend"] = pd.Series(trend, index=result.index).ffill().fillna("NA")
    return result
