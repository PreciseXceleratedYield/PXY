import warnings
from syscnfgpxy import TICKER
import numpy as np
import pandas as pd
import yfinance as yf
import os
import json

warnings.simplefilter(action='ignore', category=FutureWarning)

# Explicitly enforce Indian Standard Time zone mapping
TIMEZONE = 'Asia/Kolkata'

# 🔥 INDEPENDENT MATRIX MODE INTERFACE: 
# Format: "ST" -> First Digit = SIDE Mode, Second Digit = TREND Mode
# "72" means: If market is SIDEWAYS use Mode 7. If market is TRENDING use Mode 2.
SELECTED_MODE = "00"


def apply_ohlc_transformation(df, mode=1):
    """Executes structural, isolated mathematical transformations based on explicit modes."""
    if df.empty:
        return df

    out = df.copy()
    raw_o = df['Open'].to_numpy()
    raw_h = df['High'].to_numpy()
    raw_l = df['Low'].to_numpy()
    raw_c = df['Close'].to_numpy()

    # ⚡ Mode 0: Hyper-Sensitive Modified Close Candles
    if mode == 0:
        out['Open'] = raw_c
        out['Close'] = np.where(
            raw_c >= raw_o, (raw_c + raw_h) / 2.0, (raw_c + raw_l) / 2.0
        )
        return out

    # ⚡ Mode 1: Raw Candles
    elif mode == 1:
        return out

    # ⚡ Mode 2: OC/2
    elif mode == 2:
        out['Close'] = (raw_o + raw_c) / 2.0
        return out

    # ⚡ Mode 3: OCC/3
    elif mode == 3:
        out['Close'] = (raw_o + (2 * raw_c)) / 3.0
        return out

    # ⚡ Mode 4: OCCC/4
    elif mode == 4:
        out['Close'] = (raw_o + (3 * raw_c)) / 4.0
        return out

    # ⚡ Mode 5: OHLCC/5
    elif mode == 5:
        out['Close'] = (raw_o + raw_h + raw_l + (2 * raw_c)) / 5.0
        return out

    # ⚡ Mode 7: 7-Linear Regression & Running Average Blend (Pine Script Translation)
    elif mode == 7:
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
            
            # Safe, modern NumPy windowing tool avoiding stride-tuple interpretation errors
            windows = np.lib.stride_tricks.sliding_window_view(series, window_shape=window)

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

    # ==========================================================================
    # 🩹 FALLBACK ENGINE: Bypasses everything and returns raw JSON fallback
    # ==========================================================================
    if df.empty or len(df) < buffer_rows:
        print("Warning: yfinance data stream unavailable. Triggering direct raw nftfut.json fallback.")
        
        # Target the file in the exact same directory as this script
        current_dir = os.path.dirname(os.path.abspath(__file__))
        fut_file_path = os.path.join(current_dir, "nftfut.json")
        fallback_price = 0.0
        
        if os.path.exists(fut_file_path) and os.path.getsize(fut_file_path) > 0:
            try:
                with open(fut_file_path, "r", encoding="utf-8") as f:
                    fut_data = json.load(f)
                    if isinstance(fut_data, list) and len(fut_data) > 0:
                        fallback_price = float(fut_data[-1].get("price", 0.0))
                    elif isinstance(fut_data, dict):
                        fallback_price = float(fut_data.get("price", 0.0))
            except Exception:
                pass
                
        if fallback_price > 0:
            current_time = pd.Timestamp.now(tz=TIMEZONE)
            mock_data = {
                'Open': [fallback_price] * target_rows,
                'High': [fallback_price] * target_rows,
                'Low': [fallback_price] * target_rows,
                'Close': [fallback_price] * target_rows,
                'Volume': [0.0] * target_rows
            }
            # Create a localized time index incrementing backwards
            time_indices = [current_time - pd.Timedelta(minutes=i) for i in reversed(range(target_rows))]
            fallback_df = pd.DataFrame(mock_data, index=time_indices)
            
            # 🔥 CRITICAL EXEMPTION: Return flat raw data instantly. Skip modes, trends, and transformations.
            return fallback_df
        else:
            # Absolute recovery floor if even the JSON is unreadable or empty
            return pd.DataFrame()

    # ==========================================================================
    # ⚡ STANDARD YAHOO PIPE (Applies Modes, Trends, and Transformations)
    # ==========================================================================
    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index)

    if df.index.tz is None:
        df = df.tz_localize('UTC').tz_convert(TIMEZONE)
    else:
        df = df.tz_convert(TIMEZONE)

    # LOCAL IMPORT SHIELD: Prevents Circular Dependency Faults
    from sysstrndpxy import get_market_trend

    # Step 1: Detect current structural matrix state (TREND vs SIDE)
    market_state = get_market_trend(df)
    mode_str = str(SELECTED_MODE).strip()

    # Step 2: Independent Switch Selection Engine (PXY Universal Master Matrix)
    if len(mode_str) == 2:
        if market_state == 'SIDE':
            dynamic_mode = int(mode_str[0])  # Use 1st digit for Sideways
        else:
            dynamic_mode = int(mode_str[1])  # Use 2nd digit for Trend breakouts
    else:
        # Fallback for standard single digits
        try:
            dynamic_mode = int(mode_str)
        except ValueError:
            dynamic_mode = 1  # Raw fallback protection if parsing fails

    # Step 3: Run transformation using the isolated runtime calculated mode
    processed_df = apply_ohlc_transformation(df, mode=dynamic_mode)

    # Step 4: Safely extract execution target footprint
    return processed_df.tail(target_rows)
