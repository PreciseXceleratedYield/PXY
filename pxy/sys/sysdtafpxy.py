import json
import math
import os
import warnings
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

warnings.simplefilter(action='ignore', category=FutureWarning)

# Explicitly enforce Indian Standard Time zone mapping
TIMEZONE = str(SYSCNFGPXY_TIMEZONE)

FORCE_NIFTY_FUT = SYSDTAFPXY_FORCE_NIFTY_FUT

def apply_ohlc_transformation(df, mode=1, futures_price=None):
    """Average each OHLC field with the latest futures price when supplied."""
    if mode != 1:
        raise ValueError("DTAF only supports mode 1 (NIFTY futures-averaged OHLC).")
    if df.empty:
        return df

    out = df.copy()
    if futures_price is None:
        return out
    try:
        futures_price = float(futures_price)
    except (TypeError, ValueError) as error:
        raise ValueError("futures_price must be a finite positive number.") from error
    if not math.isfinite(futures_price) or futures_price <= 0:
        raise ValueError("futures_price must be a finite positive number.")
    for column in ("Open", "High", "Low", "Close"):
        out[column] = (out[column] + futures_price) / 2.0
    return out


def transform_market_data(df, futures_price=None):
    """Transform OHLC history using the supplied live futures price, if any."""
    if df is None or df.empty:
        return df

    return apply_ohlc_transformation(df, futures_price=futures_price)


def _read_nifty_futures_price():
    """Read the latest positive NIFTY futures price from the rolling JSON feed."""
    fut_file_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "exe", "run", "nftfut.json"
    )
    try:
        with open(fut_file_path, "r", encoding="utf-8") as f:
            fut_data = json.load(f)
    except (OSError, json.JSONDecodeError) as error:
        print(f"Warning: Could not read futures prices {fut_file_path}: {error}")
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
                "price", target_node.get("Close", target_node.get("last_price", 0.0))
            )
        )
    except (TypeError, ValueError):
        price = 0.0
    if not math.isfinite(price) or price <= 0:
        print(f"Warning: {fut_file_path} has no valid positive futures price.")
        return None
    return price



def _fetch_yf_data_production(
    period=None,
    interval=SYSDTAFPXY_DEFAULT_INTERVAL,
    target_rows=SYSDTAFPXY_DEFAULT_TARGET_ROWS,
):
    """Fetch OHLC data and average it with the latest NIFTY futures price."""
    df = pd.DataFrame()
    buffer_rows = target_rows + 5

    if not FORCE_NIFTY_FUT:
        ticker_obj = yf.Ticker(TICKER)

        # Try initial custom period if supplied
        if period is not None:
            try:
                df = ticker_obj.history(period=period, interval=interval)
            except Exception as error:
                print(f"Warning: Yahoo Finance history request failed for {period}: {error}")

        # Loop with realistic 1-minute allowable lookup horizons (dropped problematic "max")
        if df.empty or len(df) < buffer_rows:
            for search_period in ["1d", "5d", "7d"]:
                try:
                    temp_df = ticker_obj.history(period=search_period, interval=interval)
                    if not temp_df.empty:
                        temp_df = temp_df.dropna(subset=['Open', 'High', 'Low', 'Close'])
                        if len(temp_df) >= buffer_rows:
                            df = temp_df
                            break
                except Exception:
                    pass

    futures_price = _read_nifty_futures_price()

    # ==========================================================================
    # FALLBACK ENGINE: synthesize rows from the futures price if Yahoo is unavailable.
    # ==========================================================================
    if df.empty or len(df) < buffer_rows:
        if FORCE_NIFTY_FUT:
            print("Forced source: using local nftfut.json fallback.")
        else:
            print("Warning: yfinance data stream unavailable. Using nftfut.json futures fallback.")

        if futures_price is not None:
            current_time = pd.Timestamp.now(tz=TIMEZONE)
            mock_data = {
                'Open': [futures_price] * target_rows,
                'High': [futures_price] * target_rows,
                'Low': [futures_price] * target_rows,
                'Close': [futures_price] * target_rows,
                'Volume': [0.0] * target_rows
            }
            time_indices = [current_time - pd.Timedelta(minutes=i) for i in reversed(range(target_rows))]
            fallback_df = pd.DataFrame(mock_data, index=time_indices)
            fallback_df.attrs["data_fallback"] = True
            return fallback_df
        else:
            if FORCE_NIFTY_FUT:
                print("Critical Fault: local nftfut.json fallback unavailable.")
            else:
                print("Critical Fault: yfinance and local json storage pools exhausted.")
            return pd.DataFrame()

    # ==========================================================================
    if futures_price is None:
        print("Critical Fault: cannot calculate DTAF signals without a NIFTY futures price.")
        return pd.DataFrame()

    # Average each Yahoo OHLC field with the latest NIFTY futures price.
    # ==========================================================================
    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index)

    if df.index.tz is None:
        df = df.tz_localize('UTC').tz_convert(TIMEZONE)
    else:
        df = df.tz_convert(TIMEZONE)

    processed_df = transform_market_data(df, futures_price=futures_price)
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
