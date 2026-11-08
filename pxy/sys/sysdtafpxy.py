import json
import math
import os
import warnings

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


def _blend_stale_yahoo_futures_momentum(df, interval, max_age_seconds):
    """Extend stale Yahoo 1m candles using 50% of fresh futures movement.

    Never substitute a raw futures level for an index level. If a trustworthy
    overlapping futures anchor is unavailable, leave the original data intact.
    """
    if interval != "1m" or df.empty or len(df) < 2:
        return df
    now = pd.Timestamp.now(tz=TIMEZONE)
    if now.weekday() >= 5 or not (pd.Timestamp("09:15").time() <= now.time() < pd.Timestamp("15:30").time()):
        return df
    last = pd.Timestamp(df.index[-1])
    last = last.tz_localize("UTC") if last.tzinfo is None else last
    last = last.tz_convert(TIMEZONE)
    age = (now - last).total_seconds()
    if age <= max_age_seconds or age < 0:
        return df

    file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             "exe", "run", "nftfut.json")
    try:
        with open(file_path, "r", encoding="utf-8") as handle:
            records = json.load(handle)
    except (OSError, ValueError):
        return df
    if not isinstance(records, list):
        return df

    # An explicit failed latest quote must not be bypassed by older valid records.
    if not records or not isinstance(records[-1], dict):
        return df
    try:
        last_feed_price = float(records[-1].get("price"))
        if not math.isfinite(last_feed_price) or last_feed_price <= 0:
            return df
    except (ValueError, TypeError, OverflowError):
        return df

    quotes = []
    for record in records:
        if not isinstance(record, dict):
            continue
        try:
            stamp = pd.Timestamp(record["timestamp"])
            price = float(record["price"])
            if stamp.tzinfo is None or not math.isfinite(price) or price <= 0:
                continue
            quotes.append((stamp.tz_convert(TIMEZONE), price))
        except (KeyError, TypeError, ValueError, OverflowError):
            continue
    quotes.sort(key=lambda item: item[0])
    if not quotes or not (0 <= (now - quotes[-1][0]).total_seconds() <= SYSDTAFPXY_FUTURES_MAX_AGE_SECONDS):
        return df

    # Yahoo timestamps are candle starts; anchor at the end of its last candle.
    anchor_time = last + pd.Timedelta(minutes=1)
    anchors = [(t, p) for t, p in quotes if abs((t - anchor_time).total_seconds()) <= 60]
    if not anchors:
        return df
    anchor_t, anchor_price = min(anchors, key=lambda item: abs((item[0] - anchor_time).total_seconds()))
    try:
        index_close = float(df["Close"].iloc[-1])
    except (ValueError, TypeError):
        return df
    if not math.isfinite(index_close) or index_close <= 0:
        return df
    # Use half of each futures move, never the absolute futures price/premium.
    # Require continuous minute coverage: never manufacture missing price moves.
    by_minute = {}
    for stamp, price in quotes:
        if stamp <= anchor_t or stamp > now:
            continue
        bucket = stamp.floor("min")
        if bucket <= last:
            continue
        by_minute.setdefault(bucket, []).append(price)
    if not by_minute:
        return df
    extended = df.copy()
    previous_close = index_close
    previous_futures_close = anchor_price
    minute = last + pd.Timedelta(minutes=1)
    latest_minute = now.floor("min")
    while minute <= latest_minute:
        values = by_minute.get(minute)
        if not values:
            break
        close = previous_close + 0.5 * (values[-1] - previous_futures_close)
        blended_values = [previous_close + 0.5 * (value - previous_futures_close) for value in values]
        if min(blended_values) <= 0 or close <= 0:
            break
        extended.loc[minute, ["Open", "High", "Low", "Close"]] = [
            previous_close, max(previous_close, *blended_values),
            min(previous_close, *blended_values), close,
        ]
        if "Volume" in extended.columns:
            extended.loc[minute, "Volume"] = 0.0
        previous_close = close
        previous_futures_close = values[-1]
        minute += pd.Timedelta(minutes=1)
    if len(extended) == len(df):
        return df
    extended.attrs.update(df.attrs)
    extended.attrs["futures_momentum_blend"] = True
    extended.attrs["yahoo_last_timestamp"] = last.isoformat()
    return extended


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

    # ======================================================================
    # FALLBACK: synthesize rows from the futures price if Yahoo data
    # is unavailable or insufficient.
    # ======================================================================
    if df.empty or len(df) < buffer_rows:

        if FORCE_NIFTY_FUT:
            print(
                "Forced source: using local nftfut.json fallback."
            )

        else:
            print(
                "Warning: yfinance data stream unavailable. "
                "Using nftfut.json futures fallback."
            )

        if futures_price is not None:
            current_time = pd.Timestamp.now(tz=TIMEZONE)

            mock_data = {
                "Open": [futures_price] * target_rows,
                "High": [futures_price] * target_rows,
                "Low": [futures_price] * target_rows,
                "Close": [futures_price] * target_rows,
                "Volume": [0.0] * target_rows,
            }

            time_indices = [
                current_time - pd.Timedelta(minutes=i)
                for i in reversed(range(target_rows))
            ]

            fallback_df = pd.DataFrame(
                mock_data,
                index=time_indices,
            )


            fallback_df.attrs["data_fallback"] = True

            return fallback_df

        else:
            if FORCE_NIFTY_FUT:
                print(
                    "Critical Fault: local nftfut.json "
                    "fallback unavailable."
                )

            else:
                print(
                    "Critical Fault: yfinance and local json "
                    "storage pools exhausted."
                )

            return pd.DataFrame()

    # Normalize the index to the configured timezone.
    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index)

    if df.index.tz is None:
        df = df.tz_localize("UTC").tz_convert(TIMEZONE)

    else:
        df = df.tz_convert(TIMEZONE)

    # Preserve Yahoo history, adding half of fresh futures momentum only when
    # Yahoo 1m candles are delayed and a continuous, timestamped bridge exists.
    processed_df = transform_market_data(df)
    processed_df = _blend_stale_yahoo_futures_momentum(processed_df, interval, 120)

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

    processed_df = processed_df.tail(target_rows)
    processed_df.attrs["data_fallback"] = False

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
