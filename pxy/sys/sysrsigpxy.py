
"""PXY RSIG signal pipeline using the centrally configured TSMA period."""

import numpy as np
import pandas as pd

from syscnfgpxy import SYSSMAPXY_TSMA_PERIOD
from syssmapxy import calculate_moving_average
from sysdtafpxy import fetch_yf_data
from sysdthapxy import transform_dtha_ohlc


TSMA_PERIOD = SYSSMAPXY_TSMA_PERIOD


def calculate_tsma(close, period=TSMA_PERIOD):
    """Calculate TSMA using the shared PXY moving-average implementation."""

    if isinstance(period, bool) or not isinstance(period, int) or period < 2:
        raise ValueError("TSMA period must be an integer of at least 2.")

    close_series = (
        close if isinstance(close, pd.Series) else pd.Series(close)
    )
    close_series = pd.to_numeric(close_series, errors="coerce")

    return calculate_moving_average(
        close_series,
        period=period,
        variant="TSMA",
    )


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

        close = pd.to_numeric(transform_dtha_ohlc(df)["Close"], errors="coerce")
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
