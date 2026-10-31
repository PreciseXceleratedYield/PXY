# sysahpxy.py
"""Synthetic candle modes and signal-only calculation for PXY."""

import numpy as np
import pandas as pd

from syscnfgpxy import SYSDTHAPXY_CANDLE_MODE, SYSSMAPXY_TSMA_PERIOD
from syssmapxy import calculate_moving_average


VALID_MODES = {"RAW", "OC2", "HA", "OHLC4", "HYPER", "TOAC"}


def transform_ohlc(df, mode=SYSDTHAPXY_CANDLE_MODE):
    """Return OHLC candles transformed by the selected mode."""
    mode = str(mode).upper()
    if mode not in VALID_MODES:
        raise ValueError(
            "Candle mode must be RAW, OC2, HA, OHLC4, HYPER, or TOAC."
        )

    if df is None or df.empty:
        return df

    required = ("Open", "High", "Low", "Close")
    if any(column not in df.columns for column in required):
        return df.copy()

    out = df.copy()
    raw_open = pd.to_numeric(out["Open"], errors="coerce").to_numpy(dtype=float)
    raw_high = pd.to_numeric(out["High"], errors="coerce").to_numpy(dtype=float)
    raw_low = pd.to_numeric(out["Low"], errors="coerce").to_numpy(dtype=float)
    raw_close = pd.to_numeric(out["Close"], errors="coerce").to_numpy(dtype=float)

    if mode == "RAW":
        return out

    if mode == "OC2":
        out["Close"] = (raw_open + raw_close) / 2.0
        return out

    if mode == "OHLC4":
        out["Close"] = (
            raw_open + raw_high + raw_low + raw_close
        ) / 4.0
        return out

    if mode == "HYPER":
        bullish = raw_close >= raw_open
        out["Open"] = raw_close
        out["Close"] = np.where(
            bullish,
            (raw_close + raw_high) / 2.0,
            (raw_close + raw_low) / 2.0,
        )
        return out

    if mode == "TOAC":
        tsma = calculate_moving_average(
            pd.Series(raw_close, index=out.index),
            period=SYSSMAPXY_TSMA_PERIOD,
            variant="TSMA",
        ).to_numpy(dtype=float)
        out["Open"] = tsma
        out["Close"] = raw_close
        out["High"] = np.maximum.reduce((raw_high, tsma, raw_close))
        out["Low"] = np.minimum.reduce((raw_low, tsma, raw_close))
        return out

    # Standard Heikin-Ashi.
    ha_close = (raw_open + raw_high + raw_low + raw_close) / 4.0
    ha_open = np.empty(len(out), dtype=float)
    ha_open[0] = (raw_open[0] + raw_close[0]) / 2.0

    for i in range(1, len(out)):
        ha_open[i] = (ha_open[i - 1] + ha_close[i - 1]) / 2.0

    out["Open"] = ha_open
    out["High"] = np.maximum.reduce((raw_high, ha_open, ha_close))
    out["Low"] = np.minimum.reduce((raw_low, ha_open, ha_close))
    out["Close"] = ha_close
    return out


def get_signal(df, mode=SYSDTHAPXY_CANDLE_MODE):
    """Return only the latest signal: BULL, BEAR, BUY, SELL, or NONE."""
    if df is None or df.empty or len(df) < 2:
        return "NONE"

    transformed = transform_ohlc(df, mode=mode)
    if transformed is None or transformed.empty:
        return "NONE"

    mode = str(mode).upper()
    close = pd.to_numeric(transformed["Close"], errors="coerce")

    if mode == "TOAC":
        open_ = pd.to_numeric(transformed["Open"], errors="coerce")
        previous_close, current_close = close.iloc[-2], close.iloc[-1]
        previous_open, current_open = open_.iloc[-2], open_.iloc[-1]

        if not np.isfinite(
            [previous_open, current_open, previous_close, current_close]
        ).all():
            return "NONE"

        previous = (
            "UP" if previous_close > previous_open
            else "DOWN" if previous_close < previous_open
            else "FLAT"
        )
        current = (
            "UP" if current_close > current_open
            else "DOWN" if current_close < current_open
            else "FLAT"
        )
    else:
        changes = close.diff()
        if len(changes) < 3:
            return "NONE"

        previous_change, current_change = changes.iloc[-2], changes.iloc[-1]
        if not np.isfinite([previous_change, current_change]).all():
            return "NONE"

        previous = (
            "UP" if previous_change > 0
            else "DOWN" if previous_change < 0
            else "FLAT"
        )
        current = (
            "UP" if current_change > 0
            else "DOWN" if current_change < 0
            else "FLAT"
        )

    if previous == "UP" and current == "UP":
        return "BULL"
    if previous == "DOWN" and current == "DOWN":
        return "BEAR"
    if previous == "UP" and current == "DOWN":
        return "SELL"
    if previous == "DOWN" and current == "UP":
        return "BUY"
    return "NONE"
