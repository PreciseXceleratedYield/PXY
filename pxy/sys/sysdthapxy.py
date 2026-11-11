# sysdthapxy.py
import numpy as np
import pandas as pd

from syscnfgpxy import (
    SYSDTHAPXY_CANDLE_MODE,
    SYSDTHAPXY_INCLUDE_RUNNING_CANDLE,
    SYSDPTPXY_LAST_N,
    SYSSMAPXY_TSMA_PERIOD,
    SYSDTSTPXY_ST1_PERIOD,
    SYSDTSTPXY_ST1_FACTOR,
)
from syssmapxy import calculate_moving_average
from sysdtafpxy import fetch_yf_data


def _dtha_row_key(idx):
    """Use the same key for equivalent timestamps in different timezones."""
    try:
        timestamp = pd.Timestamp(idx)
        if timestamp.tzinfo is None:
            timestamp = timestamp.tz_localize("UTC")
        return timestamp.tz_convert("UTC").isoformat()
    except (TypeError, ValueError):
        return str(idx)


def _dtha_ohlc_signature(df):
    """Fingerprint OHLC values and index, excluding unrelated indicator columns."""
    values = df.loc[:, ["Open", "High", "Low", "Close"]].apply(pd.to_numeric, errors="coerce").astype(float)
    return tuple(pd.util.hash_pandas_object(values, index=False).tolist())


def transform_dtha_ohlc(df, mode=SYSDTHAPXY_CANDLE_MODE):
    """Transform raw market OHLC once using one of six pure candle modes."""
    valid_modes = {"RAW", "OC2", "OCC3", "OHLC4", "HKIN", "HYPR"}
    if mode not in valid_modes:
        raise ValueError("DTHA mode must be RAW, OC2, OCC3, OHLC4, HKIN, or HYPR.")

    if df is None or df.empty:
        return df

    required = ("Open", "High", "Low", "Close")
    if any(column not in df.columns for column in required):
        raise ValueError("DTHA requires Open, High, Low, and Close columns.")

    numeric = df.loc[:, list(required)].apply(pd.to_numeric, errors="coerce")
    if not np.isfinite(numeric.to_numpy(dtype=float)).all():
        raise ValueError("DTHA requires finite numeric OHLC candles.")
    if not (
        (numeric > 0).all().all()
        and (numeric["High"] >= numeric[["Open", "Low", "Close"]].max(axis=1)).all()
        and (numeric["Low"] <= numeric[["Open", "High", "Close"]].min(axis=1)).all()
    ):
        raise ValueError("DTHA received invalid OHLC ranges.")

    prior_mode = df.attrs.get("pxy_dtha_mode")
    if prior_mode is not None:
        prior_signature = df.attrs.get("pxy_dtha_signature")
        current_signature = _dtha_ohlc_signature(df)
        # A frame may be sliced after DTHA; compare each surviving candle
        # against its original row hash when the original index is retained.
        original_rows = df.attrs.get("pxy_dtha_rows")
        if original_rows is not None:
            if any(original_rows.get(_dtha_row_key(idx)) != h for idx, h in zip(df.index, current_signature)):
                raise ValueError("DTHA OHLC changed after transformation; provide raw candles.")
        elif prior_signature != current_signature:
            raise ValueError("DTHA OHLC changed after transformation; provide raw candles.")
        if prior_mode != mode:
            raise ValueError("Cannot transform an already transformed frame to another mode.")
        return df.copy()
    out = df.copy()
    raw_open = pd.to_numeric(out["Open"], errors="coerce").to_numpy(dtype=float)
    raw_high = pd.to_numeric(out["High"], errors="coerce").to_numpy(dtype=float)
    raw_low = pd.to_numeric(out["Low"], errors="coerce").to_numpy(dtype=float)
    raw_close = pd.to_numeric(out["Close"], errors="coerce").to_numpy(dtype=float)

    if mode == "RAW":
        out.attrs["pxy_dtha_mode"] = mode
        out.attrs["pxy_dtha_signature"] = _dtha_ohlc_signature(out)
        out.attrs["pxy_dtha_rows"] = dict(zip(map(_dtha_row_key, out.index), out.attrs["pxy_dtha_signature"]))
        return out

    if mode == "OC2":
        out["Close"] = (raw_open + raw_close) / 2.0
        out.attrs["pxy_dtha_mode"] = mode
        out.attrs["pxy_dtha_signature"] = _dtha_ohlc_signature(out)
        out.attrs["pxy_dtha_rows"] = dict(zip(map(_dtha_row_key, out.index), out.attrs["pxy_dtha_signature"]))
        return out

    if mode == "OCC3":
        out["Close"] = (raw_open + 2.0 * raw_close) / 3.0
        out.attrs["pxy_dtha_mode"] = mode
        out.attrs["pxy_dtha_signature"] = _dtha_ohlc_signature(out)
        out.attrs["pxy_dtha_rows"] = dict(zip(map(_dtha_row_key, out.index), out.attrs["pxy_dtha_signature"]))
        return out

    if mode == "OHLC4":
        out["Close"] = (
            raw_open + raw_high + raw_low + raw_close
        ) / 4.0
        out.attrs["pxy_dtha_mode"] = mode
        out.attrs["pxy_dtha_signature"] = _dtha_ohlc_signature(out)
        out.attrs["pxy_dtha_rows"] = dict(zip(map(_dtha_row_key, out.index), out.attrs["pxy_dtha_signature"]))
        return out

    if mode == "HYPR":
        bullish = raw_close >= raw_open
        hyper_close = np.where(
            bullish,
            (raw_close + raw_high) / 2.0,
            (raw_close + raw_low) / 2.0,
        )
        out["Open"] = raw_close
        out["Close"] = hyper_close
        out.attrs["pxy_dtha_mode"] = mode
        out.attrs["pxy_dtha_signature"] = _dtha_ohlc_signature(out)
        out.attrs["pxy_dtha_rows"] = dict(zip(map(_dtha_row_key, out.index), out.attrs["pxy_dtha_signature"]))
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
    out.attrs["pxy_dtha_mode"] = mode
    out.attrs["pxy_dtha_signature"] = _dtha_ohlc_signature(out)
    out.attrs["pxy_dtha_rows"] = dict(zip(map(_dtha_row_key, out.index), out.attrs["pxy_dtha_signature"]))
    return out



def export_dtha_json(df, output_path, *, orient="split", date_format="iso"):
    """Publish DTHA candle OHLC as JSON; never load JSON back into DTHA.

    Keep the caller's existing filename and pandas JSON layout. The caller
    supplies raw DTAF candles or an already-marked DTHA frame.
    """
    import os
    import tempfile

    if df is None or df.empty:
        return None
    candles = transform_dtha_ohlc(df)
    directory = os.path.dirname(os.path.abspath(output_path))
    os.makedirs(directory, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=directory,
            prefix=".dtha-", suffix=".tmp", delete=False,
        ) as handle:
            temporary = handle.name
        candles.to_json(temporary, date_format=date_format, orient=orient)
        os.replace(temporary, output_path)
        temporary = None
    finally:
        if temporary is not None and os.path.exists(temporary):
            os.unlink(temporary)
    return candles



def publish_dtha_json_payload(payload, output_path, *, indent=2):
    """Atomically publish a DTHA-derived display payload (never an input feed)."""
    import json
    import os
    import tempfile

    directory = os.path.dirname(os.path.abspath(output_path))
    os.makedirs(directory, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=directory,
            prefix=".dtha-", suffix=".tmp", delete=False,
        ) as handle:
            temporary = handle.name
            json.dump(payload, handle, indent=indent, allow_nan=False)
        os.replace(temporary, output_path)
        temporary = None
    finally:
        if temporary is not None and os.path.exists(temporary):
            os.unlink(temporary)
    return payload


def get_supr_signals(df, include_running=None):
    """Return SUPR IN/OUT from DTHA-transformed candles and SuperTrend.

    IN uses SuperTrend flips or ST/candle disagreement.\n    Flat transformed-close change gives NONE/SIDE.
    """
    from sysstrnpxy import _compute_single_st

    neutral = ("NONE", "SIDE")
    if df is None or df.empty:
        return neutral
    required = ("Open", "High", "Low", "Close")
    if any(name not in df.columns for name in required):
        return neutral
    if include_running is None:
        include_running = SYSDTHAPXY_INCLUDE_RUNNING_CANDLE == "YES"
    candles = df if include_running else df.iloc[:-1]
    if len(candles) < 2:
        return neutral
    raw = transform_dtha_ohlc(candles).loc[:, list(required)].copy()
    for name in required:
        raw[name] = pd.to_numeric(raw[name], errors="coerce")
    if not np.isfinite(raw.to_numpy(dtype=float)).all():
        return neutral
    if not (
        (raw["High"] >= raw[["Open", "Low", "Close"]].max(axis=1)).all()
        and (raw["Low"] <= raw[["Open", "High", "Close"]].min(axis=1)).all()
        and (raw > 0).all().all()
    ):
        return neutral

    closes = raw["Close"].to_numpy(dtype=float)
    change = closes[-1] - closes[-2]
    if change == 0:
        return neutral
    raw_direction = "BULL" if change > 0 else "BEAR"

    st_line, _ = _compute_single_st(raw, period=SYSDTSTPXY_ST1_PERIOD, factor=SYSDTSTPXY_ST1_FACTOR)
    if not len(st_line) or not np.isfinite(st_line[-1]):
        return neutral
    # Standard SuperTrend: price above the active band is bullish,
    # below the active band is bearish.
    if closes[-1] > st_line[-1]:
        st_direction = "BULL"
    elif closes[-1] < st_line[-1]:
        st_direction = "BEAR"
    else:
        return neutral

    # Qualify SuperTrend flips as IN signals; OUT retains raw/ST agreement behavior.
    previous_st_line = st_line[-2]
    previous_st_direction = (
        "BULL" if closes[-2] > previous_st_line
        else "BEAR" if closes[-2] < previous_st_line
        else None
    ) if np.isfinite(previous_st_line) else None
    if st_direction == raw_direction:
        out_signal = raw_direction
    else:
        out_signal = "SIDE"
    if previous_st_direction is not None and previous_st_direction != st_direction:
        return ("BUY" if st_direction == "BULL" else "SELL", out_signal)
    if st_direction == raw_direction:
        return ("NONE", out_signal)
    return ("BUY" if st_direction == "BULL" else "SELL", out_signal)


def get_stma_signals(df, include_running=None):
    """Hybrid ST + TSMA crossing: IN on a crossing, OUT by price side."""
    from sysstrnpxy import _compute_single_st

    neutral = ("NONE", "SIDE")
    if df is None or df.empty:
        return neutral
    required = ("Open", "High", "Low", "Close")
    if any(name not in df.columns for name in required):
        return neutral
    if include_running is None:
        include_running = SYSDTHAPXY_INCLUDE_RUNNING_CANDLE == "YES"
    candles = df if include_running else df.iloc[:-1]
    if len(candles) < SYSSMAPXY_TSMA_PERIOD + 1:
        return neutral
    raw = transform_dtha_ohlc(candles).loc[:, list(required)].apply(pd.to_numeric, errors="coerce")
    if not np.isfinite(raw.to_numpy(dtype=float)).all():
        return neutral

    st_line, _ = _compute_single_st(
        raw, period=SYSDTSTPXY_ST1_PERIOD, factor=SYSDTSTPXY_ST1_FACTOR
    )
    tsma = calculate_moving_average(
        raw["Close"], period=SYSSMAPXY_TSMA_PERIOD, variant="TSMA"
    ).to_numpy(dtype=float)
    hybrid = (np.asarray(st_line, dtype=float) + tsma) / 2.0
    close = raw["Close"].to_numpy(dtype=float)
    if not np.isfinite(hybrid[-2:]).all():
        return neutral

    prev_gap = close[-2] - hybrid[-2]
    gap = close[-1] - hybrid[-1]
    if gap > 0:
        return ("BUY" if prev_gap <= 0 else "NONE", "BULL")
    if gap < 0:
        return ("SELL" if prev_gap >= 0 else "NONE", "BEAR")
    return neutral


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
        if df.attrs.get("pxy_dtha_mode") is not None:
            raise ValueError("Live ticks must be injected into raw DTAF candles before DTHA.")
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

def get_stmt_states(df):
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
    return pd.Series(states, index=raw.index, name="stmt_state")
