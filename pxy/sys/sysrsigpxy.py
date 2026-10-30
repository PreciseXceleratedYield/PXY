
"""PXY RSIG signal pipeline using the centrally configured TSMA period."""

import numpy as np
import pandas as pd

from syscnfgpxy import SYSSMAPXY_TSMA_PERIOD
from sysdtafpxy import fetch_yf_data


TSMA_PERIOD = SYSSMAPXY_TSMA_PERIOD


def calculate_tsma(close, period=TSMA_PERIOD):
    """Return the rolling linear-regression endpoint TSMA series."""

    if isinstance(period, bool) or not isinstance(period, int) or period < 2:
        raise ValueError("TSMA period must be an integer of at least 2.")

    close_series = (
        close if isinstance(close, pd.Series) else pd.Series(close)
    )
    close_series = pd.to_numeric(close_series, errors="coerce")

    x = np.arange(period, dtype=float)
    x_deviations = x - x.mean()
    variance_x = np.dot(x_deviations, x_deviations)

    def regression_endpoint(values):
        if not np.all(np.isfinite(values)):
            return np.nan

        y_mean = values.mean()
        slope = np.dot(values - y_mean, x_deviations) / variance_x

        return y_mean + slope * x_deviations[-1]

    return close_series.rolling(
        window=period,
        min_periods=period,
    ).apply(regression_endpoint, raw=True)


def _none_result():
    return {
        "signal": "NONE",
        "entry_signal": "NONE",
        "exit_signal": "NONE",
        "close": None,
        "tsma": None,
        "period": TSMA_PERIOD,
    }


def get_signal_analysis(df=None):
    """Calculate the current RSIG signal from one DTAF data snapshot."""

    try:
        if df is None:
            df = fetch_yf_data()

        if (
            df is None
            or df.empty
            or "Close" not in df.columns
            or len(df) < TSMA_PERIOD
        ):
            return _none_result()

        close = pd.to_numeric(df["Close"], errors="coerce")
        tsma = calculate_tsma(close, period=TSMA_PERIOD)

        current_close = float(close.iloc[-1])
        current_tsma = float(tsma.iloc[-1])

        if not np.isfinite(current_close) or not np.isfinite(current_tsma):
            return _none_result()

        if current_close > current_tsma:
            signal = "BULL"
        elif current_close < current_tsma:
            signal = "BEAR"
        else:
            signal = "NONE"

        entry_signal = {
            "BULL": "BUY",
            "BEAR": "SELL",
        }.get(signal, "NONE")

        return {
            "signal": signal,
            "entry_signal": entry_signal,
            "exit_signal": signal,
            "close": current_close,
            "tsma": current_tsma,
            "period": TSMA_PERIOD,
        }

    except Exception:
        return _none_result()


def get_entry_signal(df=None):
    return get_signal_analysis(df)["entry_signal"]


def get_exit_signal(df=None):
    return get_signal_analysis(df)["exit_signal"]


def get_signals(df=None):
    result = get_signal_analysis(df)
    return result["entry_signal"], result["exit_signal"]


if __name__ == "__main__":
    result = get_signal_analysis()

    print(
        f"Close: {result['close']} | "
        f"TSMA({result['period']}): {result['tsma']} | "
        f"Signal: {result['signal']} | "
        f"Entry: {result['entry_signal']} | "
        f"Exit: {result['exit_signal']}"
    )
