# sysdthapxy.py
import numpy as np
import pandas as pd

from syscnfgpxy import (
    SYSDTHAPXY_CANDLE_MODE,
    SYSDTHAPXY_INCLUDE_RUNNING_CANDLE,
    SYSDPTPXY_LAST_N,
    SYSSMAPXY_TSMA_PERIOD,
)
from syssmapxy import calculate_moving_average
from sysdtafpxy import fetch_yf_data


def transform_dtha_ohlc(df, mode=SYSDTHAPXY_CANDLE_MODE):
    """Return a copy of OHLC data transformed using the selected DTHA mode.

    OC2 and OHLC4 replace Close with the corresponding candle average.
    HYPER preserves the former DTAF mode-0 transformation.
    TSMA uses TSMA open and a 3:1 weighted TSMA/real close.
    HA applies the standard recursive Heikin-Ashi transformation.
    """
    valid_modes = {"RAW", "OC2", "HA", "OHLC4", "HYPER", "TSMA"}
    if mode not in valid_modes:
        raise ValueError(
            "DTHA mode must be RAW, OC2, HA, OHLC4, HYPER, or TSMA."
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
        hyper_close = np.where(
            bullish,
            (raw_close + raw_high) / 2.0,
            (raw_close + raw_low) / 2.0,
        )
        out["Open"] = raw_close
        out["Close"] = hyper_close
        return out

    if mode == "TSMA":
        # Pine: ta.linreg(open, 7, 0)
        tsma_open = calculate_moving_average(
            pd.Series(raw_open, index=out.index),
            period=SYSSMAPXY_TSMA_PERIOD,
            variant="TSMA",
        ).to_numpy(dtype=float)

        # Pine: candle_open = tsma_open
        # Weighted synthetic close: 75% TSMA open + 25% actual close
        candle_close = (3.0 * tsma_open + raw_close) / 4.0

        # Wickless synthetic candle: range is only between its open and close.
        out["Open"] = tsma_open
        out["Close"] = candle_close
        out["High"] = np.maximum(tsma_open, candle_close)
        out["Low"] = np.minimum(tsma_open, candle_close)
        return out

    # Standard Heikin-Ashi candles.
    ha_close = (
        raw_open + raw_high + raw_low + raw_close
    ) / 4.0
    ha_open = np.empty(len(out), dtype=float)
    ha_high = np.empty(len(out), dtype=float)
    ha_low = np.empty(len(out), dtype=float)

    ha_open[0] = (raw_open[0] + raw_close[0]) / 2.0
    for i in range(1, len(out)):
        ha_open[i] = (ha_open[i - 1] + ha_close[i - 1]) / 2.0

    ha_high[:] = np.maximum.reduce((raw_high, ha_open, ha_close))
    ha_low[:] = np.minimum.reduce((raw_low, ha_open, ha_close))

    out["Open"] = ha_open
    out["High"] = ha_high
    out["Low"] = ha_low
    out["Close"] = ha_close
    return out


def get_close_direction_series(closes):
    """Return each close's direction relative to the preceding close."""
    close_series = pd.to_numeric(pd.Series(closes), errors="coerce")
    changes = close_series.diff()
    return pd.Series(
        np.select(
            [changes > 0, changes < 0, changes == 0],
            ["UP", "DOWN", "FLAT"],
            default="UNKNOWN",
        ),
        index=close_series.index,
        name="pxy_direction",
    )


def get_signal_depth_analysis(df=None, last_n=SYSDPTPXY_LAST_N, include_running=None):
    """Calculate DTHA signal and directional depths using C0/C1 close comparisons."""
    empty = {
        "signal": "NONE",
        "past_depth": "NA",
        "ce_depth": 1,
        "pe_depth": 1,
        "previous_close": None,
        "current_close": None,
    }
    if last_n <= 0:
        return empty

    if include_running is None:
        include_running = SYSDTHAPXY_INCLUDE_RUNNING_CANDLE == "YES"

    if df is None:
        df = fetch_yf_data()
    if df is None or df.empty or "Close" not in df.columns:
        return empty

    transformed = transform_dtha_ohlc(df)
    close_series = pd.to_numeric(transformed["Close"], errors="coerce")
    evaluated_closes = (
        close_series if include_running else close_series.iloc[:-1]
    )
    directions = get_close_direction_series(evaluated_closes).tolist()

    signal = "NONE"
    # C0 is the latest evaluated candle. C1 is the candle immediately before it.
    # Each candle's colour is its transformed Close versus the prior Close.
    if len(directions) >= 3:
        c1_direction, c0_direction = directions[-2:]
        if c1_direction in {"UP", "DOWN"} and c0_direction in {"UP", "DOWN"}:
            if c1_direction == "UP" and c0_direction == "UP":
                signal = "BULL"
            elif c1_direction == "DOWN" and c0_direction == "DOWN":
                signal = "BEAR"

    current_direction = directions[-1] if directions else "UNKNOWN"
    current_depth = 0
    if current_direction in {"UP", "DOWN"}:
        for direction in reversed(directions):
            if direction != current_direction:
                break
            current_depth += 1
    current_depth = max(current_depth, 1)

    current_streak_start = len(directions) - current_depth
    previous_direction = (
        directions[current_streak_start - 1]
        if current_streak_start > 0 else "UNKNOWN"
    )
    past_depth = 0
    if previous_direction in {"UP", "DOWN"}:
        prior_scan_start = max(0, current_streak_start - last_n)
        for direction in reversed(directions[prior_scan_start:current_streak_start]):
            if direction != previous_direction:
                break
            past_depth += 1
    past_depth = max(past_depth, 1)

    if previous_direction == "UP":
        past_depth_label = f"CE{past_depth}"
    elif previous_direction == "DOWN":
        past_depth_label = f"PE{past_depth}"
    else:
        past_depth_label = "NA"

    ce_depth = current_depth if current_direction == "UP" else 1
    pe_depth = current_depth if current_direction == "DOWN" else 1
    previous_close = (
        float(evaluated_closes.iloc[-2])
        if len(evaluated_closes) >= 2 and pd.notna(evaluated_closes.iloc[-2])
        else None
    )
    current_close = (
        float(evaluated_closes.iloc[-1])
        if len(evaluated_closes) >= 1 and pd.notna(evaluated_closes.iloc[-1])
        else None
    )
    signal_candle_time = (
        str(evaluated_closes.index[-1]) if len(evaluated_closes) else None
    )

    return {
        "signal": signal,
        "past_depth": past_depth_label,
        "ce_depth": ce_depth,
        "pe_depth": pe_depth,
        "previous_close": previous_close,
        "current_close": current_close,
        "signal_candle_time": signal_candle_time,
    }


def get_pxy_data(tickerSymbol=None, df=None, live_tick=None):
    """
    Processes market OHLC candles using the configured DTHA mode.
    Accepts an active live_tick dictionary to update the running candle.
    """
    if df is None:
        df = fetch_yf_data()

    if df is None or df.empty:
        return None, None, None, pd.DataFrame()

    df = df.copy()

    required_cols = ["Open", "High", "Low", "Close"]
    for col in required_cols:
        if col not in df.columns:
            return None, None, None, pd.DataFrame()

    # Inject the live market tick into the raw running candle first.
    if live_tick is not None:
        last_idx = df.index[-1]
        df.loc[last_idx, "Open"] = live_tick["Open"]
        df.loc[last_idx, "High"] = max(live_tick["High"], live_tick["Close"])
        df.loc[last_idx, "Low"] = min(live_tick["Low"], live_tick["Close"])
        df.loc[last_idx, "Close"] = live_tick["Close"]

    # All modes use transformed C0 Close versus C1 Close.
    custom_df = transform_dtha_ohlc(df)
    custom_df["pxy_direction"] = get_close_direction_series(custom_df["Close"])
    custom_df["pxy_color"] = custom_df["pxy_direction"].map(
        {"UP": "green", "DOWN": "red", "FLAT": "flat"}
    ).fillna("flat")

    final_df = custom_df.copy()
    pxy_close = final_df["Close"].copy()
    pxy_open = final_df["Open"].copy()
    pxy_color_series = final_df["pxy_color"].copy()

    return pxy_close, pxy_open, pxy_color_series, final_df

def get_tsst_states(df):
    """Classify DTHA-transformed closes using primary ST and its mirror."""
    from sysstrnpxy import calculate_supertrend

    if df is None or df.empty or len(df) < SYSSMAPXY_TSMA_PERIOD:
        return pd.Series(dtype="object")
    required = ("Open", "High", "Low", "Close")
    if any(name not in df.columns for name in required):
        return pd.Series(dtype="object")
    raw = transform_dtha_ohlc(df)
    for name in required:
        raw[name] = pd.to_numeric(raw[name], errors="coerce")
    if not np.isfinite(raw[list(required)].to_numpy(dtype=float)).all():
        return pd.Series(dtype="object")
    st_lines = calculate_supertrend(raw)
    st = st_lines["st_line"].to_numpy(dtype=float)
    mirror = st_lines["st_mirror"].to_numpy(dtype=float)
    close = raw["Close"].to_numpy(dtype=float)
    upper = np.maximum(st, mirror)
    lower = np.minimum(st, mirror)
    states = np.select(
        [close > upper, close < lower],
        ["BULL", "BEAR"], default="SIDE"
    )
    states[~(np.isfinite(upper) & np.isfinite(lower))] = "SIDE"
    return pd.Series(states, index=raw.index, name="tsst_state")
