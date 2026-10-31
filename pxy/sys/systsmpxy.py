import numpy as np
import pandas as pd

from syscnfgpxy import SYSSMAPXY_TSMA_PERIOD


def calculate_tsma(close: pd.Series, period: int = SYSSMAPXY_TSMA_PERIOD) -> pd.Series:
    """Calculate the rolling linear-regression endpoint TSMA."""
    if period < 2:
        raise ValueError("TSMA period must be at least 2.")
    if not isinstance(close, pd.Series):
        close = pd.Series(close)
    x = np.arange(period, dtype=float)
    x_deviations = x - x.mean()
    variance_x = float(np.dot(x_deviations, x_deviations))

    def regression_endpoint(values):
        mean = values.mean()
        slope = np.dot(values - mean, x_deviations) / variance_x
        return mean + slope * x_deviations[-1]

    return close.rolling(window=period).apply(regression_endpoint, raw=True)


def get_tsma(df: pd.DataFrame, period: int = SYSSMAPXY_TSMA_PERIOD) -> dict:
    """Return TSMA value and independent price-relative BULL/BEAR status."""
    if df is None or df.empty or len(df) < period:
        return {"value": 0.0, "status": "NA", "period": period, "variant": "TSMA"}
    tsma = calculate_tsma(df["Close"], period=period)
    latest_value = tsma.iloc[-1]
    if pd.isna(latest_value):
        value, status = 0.0, "NA"
    else:
        value = float(latest_value)
        status = "BULL" if float(df["Close"].iloc[-1]) >= value else "BEAR"
    return {"value": value, "status": status, "period": period, "variant": "TSMA"}
