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
    TOAC creates a TSMA-open synthetic candle using actual market close.
    HA applies the standard recursive Heikin-Ashi transformation.
    """
    valid_modes = {"RAW", "OC2", "HA", "OHLC4", "HYPER", "TOAC"}
    if mode not in valid_modes:
        raise ValueError(
            "DTHA mode must be RAW, OC2, HA, OHLC4, HYPER, or TOAC."
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
    """Calculate canonical MKT signals and directional depths from DTHA data."""
    if include_running is None:
        include_running = SYSDTHAPXY_INCLUDE_RUNNING_CANDLE == "YES"
    if last_n <= 0:
        return {
            "signal": "NONE",
            "past_depth": "NA",
            "ce_depth": 1,
            "pe_depth": 1,
            "previous_close": None,
            "current_close": None,
        }

    if df is None:
        df = fetch_yf_data()
    if df is None or df.empty or "Close" not in df.columns:
        return {
            "signal": "NONE",
            "past_depth": "NA",
            "ce_depth": 1,
            "pe_depth": 1,
            "previous_close": None,
            "current_close": None,
        }

    df = transform_dtha_ohlc(df)
    close_series = pd.to_numeric(df["Close"], errors="coerce")
    evaluated_closes = close_series if include_running else close_series.iloc[:-1]
    if SYSDTHAPXY_CANDLE_MODE == "TOAC":
        candle_open = pd.to_numeric(df["Open"], errors="coerce")
        candle_close = close_series
        evaluated_open = candle_open if include_running else candle_open.iloc[:-1]
        evaluated_close = candle_close if include_running else candle_close.iloc[:-1]
        candle_colors = np.select(
            [
                evaluated_close.to_numpy() > evaluated_open.to_numpy(),
                evaluated_close.to_numpy() < evaluated_open.to_numpy(),
            ],
            ["green", "red"],
            default="flat",
        )
        directions = [
            "UP" if color == "green"
            else "DOWN" if color == "red"
            else "FLAT"
            for color in candle_colors
        ]
    else:
        evaluated_directions = get_close_direction_series(close_series)
        directions = (
            evaluated_directions
            if include_running
            else evaluated_directions.iloc[:-1]
        ).tolist()

    closes = evaluated_closes
    signal = "NONE"

    if SYSDTHAPXY_CANDLE_MODE == "TOAC" and len(directions) >= 2:
        previous_color, current_color = directions[-2:]
        if previous_color == "UP" and current_color == "UP":
            signal = "BULL"
        elif previous_color == "DOWN" and current_color == "DOWN":
            signal = "BEAR"
        elif previous_color == "UP" and current_color == "DOWN":
            signal = "SELL"
        elif previous_color == "DOWN" and current_color == "UP":
            signal = "BUY"
    elif len(closes) >= 3:
        first_move, second_move = directions[-2:]
        if first_move == "DOWN" and second_move == "UP":
            signal = "BULL"
        elif first_move == "UP" and second_move == "DOWN":
            signal = "BEAR"
        elif first_move == "UP" and second_move == "UP":
            signal = "BULL"
        elif first_move == "DOWN" and second_move == "DOWN":
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
        directions[current_streak_start - 1] if current_streak_start > 0 else "UNKNOWN"
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
    previous_close = float(closes.iloc[-2]) if len(closes) >= 2 else None
    current_close = float(closes.iloc[-1]) if len(closes) >= 1 else None
    signal_candle_time = str(closes.index[-1]) if len(closes) else None

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

    # Apply the selected candle mode consistently before deriving direction.
    custom_df = transform_dtha_ohlc(df)
    if SYSDTHAPXY_CANDLE_MODE == "TOAC":
        custom_df["pxy_direction"] = np.select(
            [
                custom_df["Close"] > custom_df["Open"],
                custom_df["Close"] < custom_df["Open"],
            ],
            ["UP", "DOWN"],
            default="FLAT",
        )
    else:
        custom_df["pxy_direction"] = get_close_direction_series(custom_df["Close"])
    custom_df["pxy_color"] = custom_df["pxy_direction"].map(
        {"UP": "green", "DOWN": "red", "FLAT": "flat"}
    ).fillna("flat")

    if custom_df["pxy_direction"].iloc[0] == "UNKNOWN":
        first_change = custom_df["Close"].iloc[0] - custom_df["Open"].iloc[0]
        first_color = (
            "green" if first_change > 0
            else "red" if first_change < 0
            else "flat"
        )
        custom_df.iloc[0, custom_df.columns.get_loc("pxy_color")] = first_color

    final_df = custom_df.copy()
    pxy_close = final_df["Close"].copy()
    pxy_open = final_df["Open"].copy()
    pxy_color_series = final_df["pxy_color"].copy()

    return pxy_close, pxy_open, pxy_color_series, final_df
