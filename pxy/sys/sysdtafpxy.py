
import json
import math
import os
import warnings

import numpy as np
import pandas as pd
import yfinance as yf

from syscnfgpxy import (
    SYSCNFGPXY_TICKER as TICKER,
    SYSCNFGPXY_TIMEZONE,
    SYSDTAFPXY_DEFAULT_INTERVAL,
    SYSDTAFPXY_DEFAULT_TARGET_ROWS,
    SYSDTAFPXY_FORCE_NIFTY_FUT,
)
from sysmodepxy import dispatch_mode

warnings.simplefilter(action="ignore", category=FutureWarning)

# ==========================================================================
# LOCAL MODE CONFIGURATION
# ==========================================================================
# Mode 0: Dynamic Open/Close override
# Mode 1: Historical OHLC/4 close override
# Mode 2: Close = (Open + Close) / 2
# Mode 3: Close = (Close + High + Low) / 3; recalculate High/Low
# Mode 7: Close = 7-period linear-regression projection of Open
ACTIVE_MODE = 7

TIMEZONE = str(SYSCNFGPXY_TIMEZONE)

FORCE_NIFTY_FUT = SYSDTAFPXY_FORCE_NIFTY_FUT


def apply_ohlc_transformation(
    df, mode=ACTIVE_MODE, futures_price=None
):
    """Apply the selected DTAF OHLC transformation."""

    if mode not in (0, 1, 2, 3, 7):
        raise ValueError(
            "DTAF mode must be 0, 1, 2, 3, or 7."
        )

    if df is None or df.empty:
        return df

    out = df.copy()

    # 1. Blend the futures price into each OHLC field, when supplied.
    if futures_price is not None:
        try:
            futures_price = float(futures_price)
        except (TypeError, ValueError) as error:
            raise ValueError(
                "futures_price must be a finite positive number."
            ) from error

        if not math.isfinite(futures_price) or futures_price <= 0:
            raise ValueError(
                "futures_price must be a finite positive number."
            )

        for column in ("Open", "High", "Low", "Close"):
            out[column] = (
                out[column] + futures_price
            ) / 2.0

    # 2. Apply the selected mode.
    if mode == 0:
        raw_o = out["Open"]
        raw_h = out["High"]
        raw_l = out["Low"]
        raw_c = out["Close"]

        out["Open"] = raw_c
        out["Close"] = np.where(
            raw_c >= raw_o,
            (raw_c + raw_h) / 2.0,
            (raw_c + raw_l) / 2.0,
        )

        return out

    elif mode == 1:
        if len(out) > 0:
            ohlc_4 = (
                out["Open"]
                + out["High"]
                + out["Low"]
                + out["Close"]
            ) / 4.0

            latest_original_close = out["Close"].iloc[-1]

            out["Close"] = ohlc_4.shift(1)

            out.loc[
                out.index[-1], "Close"
            ] = latest_original_close

            if len(out) > 1 and pd.isna(
                out.loc[out.index[0], "Close"]
            ):
                out.loc[
                    out.index[0], "Close"
                ] = ohlc_4.iloc[0]

        return out

    elif mode == 2:
        out["Close"] = (
            out["Open"] + out["Close"]
        ) / 2.0

        return out

    elif mode == 3:
        modified_c = (
            out["Close"] + out["High"] + out["Low"]
        ) / 3.0

        raw_o = out["Open"]

        out["Close"] = modified_c
        out["High"] = np.maximum(raw_o, modified_c)
        out["Low"] = np.minimum(raw_o, modified_c)

        return out

    elif mode == 7:
        # ==================================================================
        # MODE 7: 7-PERIOD LINEAR-REGRESSION TSMA
        #
        # Open  = Original Open
        # Close = TSMA projection of Open
        # High  = Original High
        # Low   = Original Low
        #
        # Applies to historical AND running candles.
        # ==================================================================

        period = 7
        n = float(period)

        # Regression x-axis: 1, 2, 3, 4, 5, 6, 7.
        x = np.arange(1, period + 1, dtype=float)

        sum_x = float(np.sum(x))
        sum_x2 = float(np.sum(x * x))

        denominator = (
            n * sum_x2 - sum_x * sum_x
        )

        raw_open = out["Open"].to_numpy(dtype=float)

        tsma_values = np.full(
            len(raw_open),
            np.nan,
            dtype=float,
        )

        # Calculate the 7-period regression projection for every
        # candle, including the latest running candle.
        for idx in range(period - 1, len(raw_open)):
            window_y = raw_open[
                idx - period + 1:idx + 1
            ]

            if not np.all(np.isfinite(window_y)):
                continue

            sum_y = float(np.sum(window_y))

            sum_xy = float(
                np.dot(x, window_y)
            )

            slope = (
                n * sum_xy - sum_x * sum_y
            ) / denominator

            intercept = (
                sum_y - slope * sum_x
            ) / n

            # Project regression line to the 7th point.
            tsma_values[idx] = (
                intercept + slope * n
            )

        # Replace Close wherever a valid 7-period TSMA exists.
        # This includes the latest running candle.
        valid = np.isfinite(tsma_values)

        out.loc[valid, "Close"] = np.round(
            tsma_values[valid], 2
        )

        return out

    return out


def transform_market_data(
    df, futures_price=None, mode=ACTIVE_MODE
):
    """Blend futures into OHLC, then apply the selected DTAF mode."""
    if df is None or df.empty:
        return df

    return apply_ohlc_transformation(
        df,
        mode=mode,
        futures_price=futures_price,
    )


def _read_nifty_futures_price():
    """Read the latest positive NIFTY futures price from the rolling JSON feed."""
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


def _fetch_yf_data_production(
    period=None,
    interval=SYSDTAFPXY_DEFAULT_INTERVAL,
    target_rows=SYSDTAFPXY_DEFAULT_TARGET_ROWS,
):
    """Fetch OHLC data, blend futures, and apply the configured DTAF mode."""
    df = pd.DataFrame()
    buffer_rows = target_rows + 5

    if not FORCE_NIFTY_FUT:
        ticker_obj = yf.Ticker(TICKER)

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

        if df.empty or len(df) < buffer_rows:
            for search_period in ("1d", "5d", "7d"):
                try:
                    temp_df = ticker_obj.history(
                        period=search_period,
                        interval=interval,
                    )

                    if not temp_df.empty:
                        temp_df = temp_df.dropna(
                            subset=[
                                "Open",
                                "High",
                                "Low",
                                "Close",
                            ]
                        )

                        if len(temp_df) >= buffer_rows:
                            df = temp_df
                            break

                except Exception:
                    pass

    futures_price = _read_nifty_futures_price()

    # ======================================================================
    # FALLBACK: synthesize rows from futures price if Yahoo data
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

            fallback_df = apply_ohlc_transformation(
                fallback_df,
                mode=ACTIVE_MODE,
                futures_price=None,
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

    # A futures price is required for production blending.
    if futures_price is None:
        print(
            "Critical Fault: cannot calculate DTAF signals "
            "without a NIFTY futures price."
        )
        return pd.DataFrame()

    # Normalize index to configured timezone.
    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index)

    if df.index.tz is None:
        df = df.tz_localize("UTC").tz_convert(TIMEZONE)
    else:
        df = df.tz_convert(TIMEZONE)

    # Blend futures and apply active DTAF mode.
    processed_df = transform_market_data(
        df,
        futures_price=futures_price,
        mode=ACTIVE_MODE,
    )

    processed_df = processed_df.tail(target_rows)
    processed_df.attrs["data_fallback"] = False

    return processed_df


def fetch_yf_data(
    period=None,
    interval=SYSDTAFPXY_DEFAULT_INTERVAL,
    target_rows=SYSDTAFPXY_DEFAULT_TARGET_ROWS,
):
    return dispatch_mode(
        "fetch_yf_data",
        _fetch_yf_data_production,
        period=period,
        interval=interval,
        target_rows=target_rows,
        test_kwargs={"timezone": TIMEZONE},
    )
