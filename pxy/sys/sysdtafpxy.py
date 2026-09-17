import warnings
from syscnfgpxy import TICKER
import numpy as np
import pandas as pd
import yfinance as yf

warnings.simplefilter(action='ignore', category=FutureWarning)

# Explicitly enforce Indian Standard Time zone mapping
TIMEZONE = 'Asia/Kolkata'

# 🔥 PIPELINE CONFIGURATION INTERFACE: Chained Sequential Combinations
# You are completely free to pass ANY combination of digits 0 through 7 (e.g., "72", "27", "77", "572")
# The engine executes each mathematical transformation step-by-step from left to right.
SELECTED_MODE = "72"


def apply_ohlc_transformation(df, mode="1"):
    """Executes sequential, multi-stage mathematical transformations on the OHLC matrix."""
    if df.empty:
        return df

    out = df.copy()

    # Deconstruct the mode string into individual sequential execution steps
    steps = [int(d) for d in str(mode).strip()]

    # Execute each mode sequentially in a pipeline architecture
    for step in steps:
        raw_o = out['Open'].to_numpy()
        raw_h = out['High'].to_numpy()
        raw_l = out['Low'].to_numpy()
        raw_c = out['Close'].to_numpy()

        # ⚡ Mode 0: Hyper-Sensitive Modified Close Candles
        if step == 0:
            out['Open'] = raw_c
            out['Close'] = np.where(
                raw_c >= raw_o, (raw_c + raw_h) / 2.0, (raw_c + raw_l) / 2.0
            )

        # ⚡ Mode 1: Raw Candles (Pass-through)
        elif step == 1:
            continue

        # ⚡ Mode 2: OC/2 Smoothing Matrix
        elif step == 2:
            out['Close'] = (raw_o + raw_c) / 2.0

        # ⚡ Mode 3: OCC/3 Weighted Matrix
        elif step == 3:
            out['Close'] = (raw_o + (2 * raw_c)) / 3.0

        # ⚡ Mode 4: OCCC/4 Weighted Matrix
        elif step == 4:
            out['Close'] = (raw_o + (3 * raw_c)) / 4.0

        # ⚡ Mode 5: OHLCC/5 Full-Range Matrix
        elif step == 5:
            out['Close'] = (raw_o + raw_h + raw_l + (2 * raw_c)) / 5.0

        # ⚡ Mode 7: 7-Period Linear Regression & Running Average Blend (Pine Script Translation)
        elif step == 7:
            n = len(df)
            window = 7

            # --- 1. Vectorized 7-Period Time Series Linear Regression ---
            x = np.arange(window)
            x_mean = x.mean()
            x_dev = x - x_mean
            x_var = np.sum(x_dev**2)

            def rolling_linreg(series):
                if len(series) < window:
                    return series
                # Slice array into rolling windows via numpy stride tricks
                shape = (len(series) - window + 1, window)
                strides = (series.strides, series.strides)
                windows = np.lib.stride_tricks.as_strided(
                    series, shape=shape, strides=strides
                )

                # Vectorwise OLS calculation across the window matrix
                y_means = windows.mean(axis=1, keepdims=True)
                slopes = np.sum((windows - y_means) * x_dev, axis=1) / x_var
                intercepts = y_means.flatten() - slopes * x_mean

                # Project the linear trend at current bar (offset 0)
                lr_current = intercepts + slopes * (window - 1)
                return np.concatenate([series[: window - 1], lr_current])

            lr_o = rolling_linreg(raw_o)
            lr_h = rolling_linreg(raw_h)
            lr_l = rolling_linreg(raw_l)
            lr_c = rolling_linreg(raw_c)

            # --- 2. Running Average (Cumulative Mean Breakdown) ---
            bar_count = np.arange(1, n + 1)
            ra_o = np.cumsum(raw_o) / bar_count
            ra_h = np.cumsum(raw_h) / bar_count
            ra_l = np.cumsum(raw_l) / bar_count
            ra_c = np.cumsum(raw_c) / bar_count

            # --- 3. Assign Balanced Mean Back to the Pipeline DataFrame ---
            out['Open'] = (lr_o + ra_o) / 2.0
            out['High'] = (lr_h + ra_h) / 2.0
            out['Low'] = (lr_l + ra_l) / 2.0
            out['Close'] = (lr_c + ra_c) / 2.0

    return out


def fetch_yf_data(period=None, interval="1m", target_rows=60):
    """Dynamic historical ingestion engine utilizing vectorized structural transformations"""
    ticker_obj = yf.Ticker(TICKER)
    df = pd.DataFrame()
    buffer_rows = target_rows + 5

    if period is not None:
        try:
            df = ticker_obj.history(period=period, interval=interval)
        except Exception:
            pass

    if df.empty:
        for search_period in ["5d", "7d", "max"]:
            try:
                df = ticker_obj.history(period=search_period, interval=interval)
                if not df.empty:
                    df.dropna(
                        subset=['Open', 'High', 'Low', 'Close'], inplace=True
                    )
                    if len(df) >= buffer_rows:
                        break
            except Exception:
                pass

    if df.empty or len(df) < buffer_rows:
        return pd.DataFrame()

    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index)

    if df.index.tz is None:
        df = df.tz_localize('UTC').tz_convert(TIMEZONE)
    else:
        df = df.tz_convert(TIMEZONE)

    # ==========================================================================
    # ⚡ LOCAL IMPORT SHIELD: Prevents Circular Dependency Faults
    # ==========================================================================
    from sysstrndpxy import get_market_trend

    # Step 1: Detect current structural matrix state (TREND vs SIDE)
    market_state = get_market_trend(df)
    mode_str = str(SELECTED_MODE).strip()

    # Step 2: Dynamic Universal Switch Engine (Inject Mode 0 protection if SIDE)
    if market_state == 'SIDE':
        if not mode_str.startswith("0"):
            mode_str = "0" + mode_str

    # Step 3: Run pipeline calculation over full history to lock cumulative formulas
    processed_df = apply_ohlc_transformation(df, mode=mode_str)

    # Step 4: Safely extract execution target footprint
    return processed_df.tail(target_rows)

