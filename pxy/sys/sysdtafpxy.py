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


def _blend_stale_yahoo_futures_momentum(df, interval, max_age_seconds):
    """Use the literal 50/50 index/futures average when Yahoo 1m data is stale.

    Only the current synthetic candle is added. Never rewrite the historical
    Yahoo candles or manufacture a minute-by-minute futures history.
    """
    if interval != "1m" or df.empty or len(df) < 2:
        return df
    now = pd.Timestamp.now(tz=TIMEZONE)
    if now.weekday() >= 5 or not (
        pd.Timestamp("09:15").time() <= now.time()
        < pd.Timestamp("15:30").time()
    ):
        return df

    last = pd.Timestamp(df.index[-1])
    last = last.tz_localize("UTC") if last.tzinfo is None else last
    last = last.tz_convert(TIMEZONE)
    if not (0 <= (now - last).total_seconds()) or (
        now - last
    ).total_seconds() <= max_age_seconds:
        return df

    # Strict 60-second freshness is retained for DTAF, independent of the
    # longer futures-price tolerance used by syspxy.
    futures_price = _read_nifty_futures_price()
    if futures_price is None:
        return df
    try:
        index_price = float(df["Close"].iloc[-1])
    except (TypeError, ValueError, OverflowError):
        return df
    if not math.isfinite(index_price) or index_price <= 0:
        return df

    blended_close = (index_price + futures_price) / 2.0
    minute = now.floor("min")
    if minute <= last:
        return df

    # Open at the last Yahoo close, so any futures/spot basis gap is visible
    # rather than silently hidden from the indicators.
    extended = df.copy()
    extended.loc[minute, ["Open", "High", "Low", "Close"]] = [
        index_price,
        max(index_price, blended_close),
        min(index_price, blended_close),
        blended_close,
    ]
    if "Volume" in extended.columns:
        extended.loc[minute, "Volume"] = 0.0
    extended.attrs.update(df.attrs)
    extended.attrs["futures_price_average_fallback"] = True
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
    # YF-only indicator candles: never manufacture historical OHLC from
    # a single futures quote. Return unavailable if YF has insufficient data.
    if df.empty or len(df) < buffer_rows:
        print("Warning: Yahoo NIFTY candle history unavailable or insufficient.")
        return pd.DataFrame()

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

    # Preserve Yahoo history; append one synthetic current candle only when
    # Yahoo is stale and the futures quote passes its 60-second receipt-age gate.
    processed_df = _blend_stale_yahoo_futures_momentum(
        processed_df, interval, SYSDTAFPXY_YAHOO_MAX_AGE_SECONDS
    )
    fallback_active = bool(processed_df.attrs.get("futures_price_average_fallback", False))
    processed_df = processed_df.tail(target_rows)
    processed_df.attrs["data_fallback"] = False
    processed_df.attrs["futures_price_average_fallback"] = fallback_active

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
