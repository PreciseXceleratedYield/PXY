import json
import math
import os
import warnings
import tempfile

import numpy as np
import pandas as pd
import yfinance as yf

from syscnfgpxy import (
    SYSCNFGPXY_TICKER as TICKER,
    SYSMONPXY_TICKER,
    SYSCNFGPXY_TIMEZONE,
    SYSDTAFPXY_DEFAULT_INTERVAL,
    SYSDTAFPXY_DEFAULT_TARGET_ROWS,
    SYSDTAFPXY_FUTURES_MAX_AGE_SECONDS,
    SYSDTAFPXY_YAHOO_MAX_AGE_SECONDS,
    SYSDTAFPXY_FALLBACK_PERIODS,
    SYSDTAFPXY_FORCE_NIFTY_FUT,
)

warnings.simplefilter(action="ignore", category=FutureWarning)


# Explicitly enforce configured timezone mapping.
TIMEZONE = str(SYSCNFGPXY_TIMEZONE)

FORCE_NIFTY_FUT = SYSDTAFPXY_FORCE_NIFTY_FUT


def apply_ohlc_transformation(df, futures_price=None):
    """Preserve raw OHLC for all signal and indicator calculations."""
    if df is None or df.empty:
        return df
    return df.copy()


def transform_market_data(df, futures_price=None):
    """Return raw OHLC; price blending belongs exclusively to syspxy."""
    return apply_ohlc_transformation(df)


def _read_nifty_futures_price(max_age_seconds=None):
    """Read the latest positive timestamped futures quote within the age limit."""
    if max_age_seconds is None:
        max_age_seconds = SYSDTAFPXY_FUTURES_MAX_AGE_SECONDS

    fut_file_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "exe",
        "run",
        "nftfut.json",
    )

    try:
        with open(fut_file_path, "r", encoding="utf-8") as f:
            fut_data = json.load(f)

    except (OSError, json.JSONDecodeError) as error:
        print(
            f"Warning: Could not read futures prices "
            f"{fut_file_path}: {error}"
        )
        return None

    if isinstance(fut_data, list) and fut_data:
        target_node = fut_data[-1]

    elif isinstance(fut_data, dict):
        target_node = fut_data

    else:
        target_node = {}

    if not isinstance(target_node, dict):
        target_node = {}

    # A quote without a valid, recent receipt timestamp is unavailable.
    # The feed refreshes every 5 seconds; the configured age allows brief
    # scheduling/API delays without blending an old market price.
    timestamp = target_node.get("timestamp")
    try:
        quote_time = pd.Timestamp(timestamp)
        if pd.isna(quote_time) or quote_time.tzinfo is None:
            raise ValueError("missing or timezone-naive timestamp")

        quote_time = quote_time.tz_convert(TIMEZONE)
        now = pd.Timestamp.now(tz=TIMEZONE)
        quote_age_seconds = (now - quote_time).total_seconds()

        if (
            quote_age_seconds < 0
            or quote_age_seconds > max_age_seconds
        ):
            print(
                f"Warning: {fut_file_path} futures quote is stale "
                f"or future-dated (age={quote_age_seconds:.1f}s; "
                f"maximum={max_age_seconds}s)."
            )
            return None

    except (TypeError, ValueError, OverflowError) as error:
        print(
            f"Warning: {fut_file_path} has no valid futures timestamp: {error}"
        )
        return None

    try:
        price = float(
            target_node.get(
                "price",
                target_node.get(
                    "Close",
                    target_node.get("last_price", 0.0),
                ),
            )
        )

    except (TypeError, ValueError):
        price = 0.0

    if not math.isfinite(price) or price <= 0:
        print(
            f"Warning: {fut_file_path} has no valid "
            f"positive futures price."
        )
        return None

    return price


def _read_futures_quote():
    """Return (price, receipt timestamp) only for a fresh futures quote."""
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "exe", "run", "nftfut.json")
    try:
        with open(path, encoding="utf-8") as handle:
            payload = json.load(handle)
        if isinstance(payload, list):
            payload = payload[-1] if payload else {}
        if not isinstance(payload, dict):
            return None
        stamp = pd.Timestamp(payload.get("timestamp"))
        if pd.isna(stamp) or stamp.tzinfo is None:
            return None
        stamp = stamp.tz_convert(TIMEZONE)
        age = (pd.Timestamp.now(tz=TIMEZONE) - stamp).total_seconds()
        price = float(payload.get("price", payload.get("Close", payload.get("last_price", 0))))
        if not (0 <= age <= SYSDTAFPXY_FUTURES_MAX_AGE_SECONDS
                and math.isfinite(price) and price > 0):
            return None
        return price, stamp
    except (OSError, ValueError, TypeError, OverflowError, json.JSONDecodeError):
        return None


def _continuous_signal_candles(yahoo, interval, target_rows):
    """Append timestamped source candles without replaying or repricing history.

    Futures minute OHLC is assembled from successive received quotes. The
    continuity offset belongs to the signal stream only, never order pricing.
    State survives engine process restarts and resets each exchange day.
    """
    if interval != "1m":
        return yahoo

    now = pd.Timestamp.now(tz=TIMEZONE)
    last_yahoo = (pd.Timestamp(yahoo.index[-1]).tz_convert(TIMEZONE)
                  if not yahoo.empty else None)
    yahoo_age = (now - last_yahoo).total_seconds() if last_yahoo is not None else float("inf")
    yahoo_fresh = 0 <= yahoo_age <= SYSDTAFPXY_YAHOO_MAX_AGE_SECONDS
    in_session = (now.weekday() < 5 and
                  pd.Timestamp("09:15").time() <= now.time() <
                  pd.Timestamp("15:30").time())
    quote = _read_futures_quote() if in_session else None
    state_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              "exe", "run", "dtaf_source_state.json")
    state = {}
    try:
        with open(state_path, encoding="utf-8") as handle:
            state = json.load(handle)
        if state.get("day") != now.date().isoformat():
            state = {}
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        state = {}

    fields = ["Open", "High", "Low", "Close"]
    history = []
    for item in state.get("candles", []):
        try:
            stamp = pd.Timestamp(item["time"])
            if stamp.tzinfo is None:
                continue
            vals = [float(item[field]) for field in fields]
            if all(math.isfinite(v) and v > 0 for v in vals):
                history.append((stamp.tz_convert(TIMEZONE), vals))
        except (KeyError, ValueError, TypeError, OverflowError):
            continue
    history.sort(key=lambda item: item[0])
    history = list(dict(history).items())
    if not history and not yahoo.empty:
        history = [(stamp, [float(row[field]) for field in fields])
                   for stamp, row in yahoo.tail(max(target_rows, 90)).iterrows()]
        state = {"source": "YAHOO", "offset": 0.0}
    if not history:
        # A single futures quote cannot reconstruct the indicator lookback.
        # Fail closed until real Yahoo history or same-day persisted history exists.
        return pd.DataFrame()

    source = str(state.get("source", "YAHOO"))
    offset = float(state.get("offset", 0.0))
    if not math.isfinite(offset):
        offset = 0.0
    last_time, last_vals = history[-1]
    last_close = last_vals[3]
    chosen = "YAHOO" if yahoo_fresh else ("FUTURES" if quote else "STALE")

    if chosen == "YAHOO":
        # On return to Yahoo, anchor the first unseen Yahoo bar to the
        # previously published close. Never rewrite earlier futures candles.
        unseen = yahoo[yahoo.index > last_time]
        if not unseen.empty:
            if source != "YAHOO":
                first = unseen.iloc[0]
                offset = last_close - float(first["Open"])
            for stamp, row in unseen.iterrows():
                vals = [float(row[field]) + offset for field in fields]
                if all(math.isfinite(v) and v > 0 for v in vals):
                    history.append((stamp, vals))
            source = "YAHOO"
        elif source == "YAHOO":
            # Update an in-progress Yahoo bar, retaining its existing offset.
            if last_time == last_yahoo:
                row = yahoo.iloc[-1]
                history[-1] = (last_time, [float(row[field]) + offset for field in fields])
        # If Yahoo recovers within an already published futures minute,
        # keep that minute unchanged and switch at the next Yahoo minute.
    elif chosen == "FUTURES":
        price, stamp = quote
        minute = stamp.floor("min")
        if source != "FUTURES":
            offset = last_close - price
        adjusted = price + offset
        if minute > last_time:
            history.append((minute, [last_close, max(last_close, adjusted),
                                     min(last_close, adjusted), adjusted]))
            source = "FUTURES"
        elif minute == last_time and source == "FUTURES":
            vals = history[-1][1]
            history[-1] = (minute, [vals[0], max(vals[1], adjusted),
                                    min(vals[2], adjusted), adjusted])

    # The previous session's history is never used as a continuity anchor.
    history = history[-max(target_rows, 90):]
    result = pd.DataFrame([vals for _, vals in history],
                          index=pd.DatetimeIndex([stamp for stamp, _ in history]),
                          columns=fields)
    if "Volume" in yahoo.columns:
        result["Volume"] = 0.0
    result.attrs["market_data_source"] = source
    result.attrs["market_data_fresh"] = bool(
        chosen == "YAHOO" or (chosen == "FUTURES" and source == "FUTURES"))
    result.attrs["futures_price_average_fallback"] = False
    result.attrs["data_fallback"] = False
    result.attrs["yahoo_last_timestamp"] = last_yahoo.isoformat() if last_yahoo is not None else None

    # No runtime state writes during off-hours, and no invented future candles.
    if in_session and chosen != "STALE":
        payload = {
            "day": now.date().isoformat(), "source": source,
            "offset": offset,
            "candles": [{"time": stamp.isoformat(), **dict(zip(fields, vals))}
                        for stamp, vals in history],
        }
        os.makedirs(os.path.dirname(state_path), exist_ok=True)
        tmp = None
        try:
            with tempfile.NamedTemporaryFile("w", encoding="utf-8",
                    dir=os.path.dirname(state_path), prefix=".dtaf-",
                    suffix=".tmp", delete=False) as handle:
                tmp = handle.name
                json.dump(payload, handle, allow_nan=False)
            os.replace(tmp, state_path)
            tmp = None
        finally:
            if tmp and os.path.exists(tmp):
                os.unlink(tmp)
    return result


def _fetch_yf_data_production(
    period=None,
    interval=SYSDTAFPXY_DEFAULT_INTERVAL,
    target_rows=SYSDTAFPXY_DEFAULT_TARGET_ROWS,
):
    """Fetch raw OHLC; retain futures-only fallback when Yahoo is unavailable."""

    df = pd.DataFrame()
    buffer_rows = target_rows + 5

    if not FORCE_NIFTY_FUT:
        ticker_obj = yf.Ticker(TICKER)

        # Try the requested period first, when supplied.
        if period is not None:
            try:
                df = ticker_obj.history(
                    period=period,
                    interval=interval,
                )

            except Exception as error:
                print(
                    f"Warning: Yahoo Finance history request failed "
                    f"for {period}: {error}"
                )

        # Try supported lookup horizons if the data is insufficient.
        if df.empty or len(df) < buffer_rows:
            for search_period in SYSDTAFPXY_FALLBACK_PERIODS:
                try:
                    temp_df = ticker_obj.history(
                        period=search_period,
                        interval=interval,
                    )

                    if not temp_df.empty:
                        temp_df = temp_df.dropna(
                            subset=["Open", "High", "Low", "Close"]
                        )

                        if len(temp_df) >= buffer_rows:
                            df = temp_df
                            break

                except Exception:
                    pass

    futures_price = _read_nifty_futures_price()

    # A Yahoo outage can use same-day persisted DTAF history plus fresh futures.
    # Never create a synthetic history from only one futures quote.
    if df.empty or len(df) < buffer_rows:
        print("Warning: Yahoo NIFTY candle history unavailable or insufficient; "
              "trying persisted DTAF continuity state.")
        return _continuous_signal_candles(pd.DataFrame(), interval, target_rows)

    # Normalize the index to the configured timezone.
    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index)

    if df.index.tz is None:
        df = df.tz_localize("UTC").tz_convert(TIMEZONE)

    else:
        df = df.tz_convert(TIMEZONE)

    # Indicators receive only unmodified Yahoo NIFTY OHLC candles.
    processed_df = transform_market_data(df)

    # Publish the two actual quotes already read above; never infer either
    # from transformed candles or perform an extra market-data request.
    try:
        import tempfile
        quote_path = os.path.abspath(os.path.join(
            os.path.dirname(__file__), "..", "web", "webprcpxy.json"
        ))
        os.makedirs(os.path.dirname(quote_path), exist_ok=True)
        raw_index = float(df["Close"].iloc[-1])
        index_valid = math.isfinite(raw_index) and raw_index > 0
        quote = {
            "index": raw_index if index_valid else None,
            "fut": futures_price,
            "index_time": df.index[-1].isoformat(),
        }
        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=os.path.dirname(quote_path),
                prefix=".webprcpxy.", suffix=".tmp", delete=False
            ) as handle:
                temp_path = handle.name
                json.dump(quote, handle, allow_nan=False)
            os.replace(temp_path, quote_path)
            temp_path = None
        finally:
            if temp_path and os.path.exists(temp_path):
                os.unlink(temp_path)
    except (OSError, ValueError, TypeError, OverflowError):
        pass

    processed_df = _continuous_signal_candles(processed_df, interval, target_rows)
    metadata = dict(processed_df.attrs)
    processed_df = processed_df.tail(target_rows).copy()
    processed_df.attrs.update(metadata)

    return processed_df



def fetch_yf_data_for_monitor(
    ticker=SYSMONPXY_TICKER,
    period=None,
    interval=SYSDTAFPXY_DEFAULT_INTERVAL,
    target_rows=SYSDTAFPXY_DEFAULT_TARGET_ROWS,
):
    """Fetch monitor-only Yahoo Finance data without production futures blending.

    This path is intentionally separate from fetch_yf_data(), which remains
    the NIFTY production ingestion path and retains its futures/DTAF behavior.
    """
    if os.environ.get("PXY_MONITOR_MODE") != "1":
        raise RuntimeError(
            "Monitor data is restricted to the pxymon process."
        )
    if ticker != SYSMONPXY_TICKER:
        raise ValueError(
            f"Monitor ticker is fixed to {SYSMONPXY_TICKER}."
        )
    if not isinstance(ticker, str) or not ticker.strip():
        raise ValueError("Monitor ticker must be a non-empty string.")
    if (
        isinstance(target_rows, bool)
        or not isinstance(target_rows, int)
        or target_rows < 1
    ):
        raise ValueError("target_rows must be a positive integer.")

    ticker = ticker.strip()
    buffer_rows = target_rows
    ticker_obj = yf.Ticker(ticker)
    df = pd.DataFrame()

    periods = []
    if period is not None:
        periods.append(period)
    periods.extend(
        item for item in SYSDTAFPXY_FALLBACK_PERIODS
        if item not in periods
    )

    for search_period in periods:
        try:
            candidate = ticker_obj.history(
                period=search_period,
                interval=interval,
            )
            if candidate is None or candidate.empty:
                continue
            candidate = candidate.dropna(
                subset=["Open", "High", "Low", "Close"]
            )
            if len(candidate) >= buffer_rows:
                df = candidate
                break
            if df.empty or len(candidate) > len(df):
                df = candidate
        except Exception:
            continue

    if df.empty:
        return pd.DataFrame()

    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index)

    if df.index.tz is None:
        df = df.tz_localize("UTC").tz_convert(TIMEZONE)
    else:
        df = df.tz_convert(TIMEZONE)

    df = df.tail(target_rows).copy()
    df.attrs["data_fallback"] = False
    df.attrs["source_ticker"] = ticker
    return df


def fetch_yf_data(
    period=None,
    interval=SYSDTAFPXY_DEFAULT_INTERVAL,
    target_rows=SYSDTAFPXY_DEFAULT_TARGET_ROWS,
):
    return _fetch_yf_data_production(
        period=period,
        interval=interval,
        target_rows=target_rows,
    )
