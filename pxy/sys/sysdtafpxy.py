import json
import os
import warnings
import numpy as np
import pandas as pd
import yfinance as yf
from syscnfgpxy import TICKER

warnings.simplefilter(action='ignore', category=FutureWarning)

# Explicitly enforce Indian Standard Time zone mapping
TIMEZONE = 'Asia/Kolkata'

# 🔥 INDEPENDENT MATRIX MODE INTERFACE:
# Format: "ST" -> First Digit = SIDE Mode, Second Digit = TREND Mode
# Set SELECTED_MODE to "8" (or use your string logic) to run the new Renko system.
SELECTED_MODE = "88" 

def apply_ohlc_transformation(df, mode=1, atr_period=14, fixed_brick_size=2.0):
    """Executes structural, isolated mathematical transformations based on explicit modes.
    
    Modes 0-7: Time-based mathematical variations (Heikin-Ashi, Linear Regression, etc.)
    Mode 8: Dynamic Volatility-Adaptive Renko Bricks (Clamped between 5.0 and 10.0 points)
    """
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

    # ⚡ Mode 6: True Heikin-Ashi Candles (Sequential Path Dependency)
    elif mode == 6:
        n = len(df)
        ha_c = (raw_o + raw_h + raw_l + raw_c) / 4.0
        ha_o = raw_o.copy()
        for i in range(1, n):
            ha_o[i] = (ha_o[i-1] + ha_c[i-1]) / 2.0
        ha_h = np.maximum(raw_h, np.maximum(ha_o, ha_c))
        ha_l = np.minimum(raw_l, np.minimum(ha_o, ha_c))
        out['Open'] = ha_o
        out['High'] = ha_h
        out['Low'] = ha_l
        out['Close'] = ha_c
        return out

    # ⚡ Mode 7: 7-Linear Regression & Running Average Blend (Pine Script Translation)
    elif mode == 7:
        n = len(df)
        window = 7
        if n < window:
            return out
        x = np.arange(window)
        x_mean = x.mean()
        x_dev = x - x_mean
        x_var = np.sum(x_dev**2)

        def rolling_linreg(series):
            windows = np.lib.stride_tricks.sliding_window_view(series, window_shape=window)
            y_means = windows.mean(axis=1, keepdims=True)
            slopes = np.sum((windows - y_means) * x_dev, axis=1) / x_var
            intercepts = y_means.flatten() - slopes * x_mean
            lr_current = intercepts + slopes * (window - 1)
            return np.concatenate([series[: window - 1], lr_current])

        lr_o = rolling_linreg(raw_o)
        lr_h = rolling_linreg(raw_h)
        lr_l = rolling_linreg(raw_l)
        lr_c = rolling_linreg(raw_c)

        bar_count = np.arange(1, n + 1)
        ra_o = np.cumsum(raw_o) / bar_count
        ra_h = np.cumsum(raw_h) / bar_count
        ra_l = np.cumsum(raw_l) / bar_count
        ra_c = np.cumsum(raw_c) / bar_count

        out['Open'] = (lr_o + ra_o) / 2.0
        out['High'] = (lr_h + ra_h) / 2.0
        out['Low'] = (lr_l + ra_l) / 2.0
        out['Close'] = (lr_c + ra_c) / 2.0
        return out

    # ⚡ Mode 8: Dynamic ATR Renko Bricks with Strict 5-10 Range Clamping
    elif mode == 8:
        n = len(df)
        if n <= atr_period:
            return out  # Not enough data to compute ATR
            
        # 1. Compute True Range (TR)
        prev_close_shifted = np.roll(raw_c, 1)
        prev_close_shifted[0] = raw_o[0]  # Prevent structural index boundaries tracking errors
        
        tr1 = raw_h - raw_l
        tr2 = np.abs(raw_h - prev_close_shifted)
        tr3 = np.abs(raw_l - prev_close_shifted)
        true_range = np.maximum(tr1, np.maximum(tr2, tr3))
        
        # 2. Compute Wilder's ATR (Standard Terminal Smoothing Multiplier)
        atr = np.zeros(n)
        atr[atr_period] = np.mean(true_range[1:atr_period+1])
        for i in range(atr_period + 1, n):
            atr[i] = (atr[i-1] * (atr_period - 1) + true_range[i]) / atr_period
            
        # 🔒 Strictly clamp the dynamic brick size boundary between 5 and 10 points
        renko_brick_size = np.clip(atr[-1], 5.0, 10.0)
        
        # Fallback guardrail for low liquidity or structural computational errors
        if renko_brick_size <= 0 or np.isnan(renko_brick_size):
            renko_brick_size = fixed_brick_size

        # 3. Generate Structural Renko Brick Arrays
        renko_ops = []
        renko_cl_list = []
        
        # Anchor the baseline price block cleanly based on calculations
        prev_close = np.floor(raw_c[0] / renko_brick_size) * renko_brick_size
        
        for price in raw_c:
            gap = price - prev_close
            if gap >= renko_brick_size:
                bricks = int(gap // renko_brick_size)
                for _ in range(bricks):
                    next_close = prev_close + renko_brick_size
                    renko_ops.append(prev_close)
                    renko_cl_list.append(next_close)
                    prev_close = next_close
            elif gap <= -renko_brick_size:
                bricks = int(abs(gap) // renko_brick_size)
                for _ in range(bricks):
                    next_close = prev_close - renko_brick_size
                    renko_ops.append(prev_close)
                    renko_cl_list.append(next_close)
                    prev_close = next_close
                    
        if not renko_ops:
            renko_ops.append(prev_close)
            renko_cl_list.append(prev_close)

        # 4. Construct Output Price Data Engine (FIXED LENGTH INTERFACE)
        renko_df = pd.DataFrame()
        renko_df['Open'] = renko_ops
        renko_df['Close'] = renko_cl_list
        renko_df['High'] = np.maximum(renko_df['Open'], renko_df['Close'])
        renko_df['Low'] = np.minimum(renko_df['Open'], renko_df['Close'])
        
        # Dynamically map tracking time indexes or fall back to linear integers safely
        if len(renko_ops) <= len(df):
            renko_df.index = df.index[:len(renko_ops)]
            if 'Volume' in df.columns:
                renko_df['Volume'] = df['Volume'].iloc[:len(renko_ops)].values
        else:
            # If Renko bricks outnumber the historical base data bars:
            extended_index = list(df.index)
            last_timestamp = df.index[-1]
            # Pad out missing trailing structural blocks cleanly using standard ranges
            for extra_idx in range(len(renko_ops) - len(df)):
                extended_index.append(last_timestamp)
            renko_df.index = extended_index
            
            if 'Volume' in df.columns:
                # Distribute historical volume across extra brick generation spaces evenly
                base_vol = df['Volume'].to_numpy()
                renko_df['Volume'] = np.concatenate([base_vol, np.zeros(len(renko_ops) - len(df))])

        return renko_df

    return out

def fetch_yf_data(period=None, interval="1m", target_rows=60):
    """Dynamic historical ingestion engine utilizing vectorized structural transformations"""
    ticker_obj = yf.Ticker(TICKER)
    df = pd.DataFrame()
    buffer_rows = target_rows + 5

    # Try initial custom period if supplied
    if period is not None:
        try:
            df = ticker_obj.history(period=period, interval=interval)
        except Exception:
            pass

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

    # ==========================================================================
    # 🩹 FALLBACK ENGINE: Bypasses everything and returns raw JSON fallback
    # ==========================================================================
    if df.empty or len(df) < buffer_rows:
        print("Warning: yfinance data stream unavailable. Triggering direct raw nftfut.json fallback.")
        
        current_dir = os.path.dirname(os.path.abspath(__file__))
        fut_file_path = os.path.join(current_dir, "nftfut.json")
        fallback_price = 0.0
        
        if os.path.exists(fut_file_path) and os.path.getsize(fut_file_path) > 0:
            try:
                with open(fut_file_path, "r", encoding="utf-8") as f:
                    fut_data = json.load(f)
                    # Adaptive dictionary check covering 'price', 'Close', or value indexing variants
                    if isinstance(fut_data, list) and len(fut_data) > 0:
                        target_node = fut_data[-1]
                    elif isinstance(fut_data, dict):
                        target_node = fut_data
                    else:
                        target_node = {}
                        
                    fallback_price = float(target_node.get("price", target_node.get("Close", target_node.get("last_price", 0.0))))
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
            time_indices = [current_time - pd.Timedelta(minutes=i) for i in reversed(range(target_rows))]
            fallback_df = pd.DataFrame(mock_data, index=time_indices)
            return fallback_df
        else:
            # Absolute recovery floor if even the JSON fallback path yields nothing
            print("Critical Fault: yfinance and local json storage pools exhausted.")
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

    market_state = get_market_trend(df)
    mode_str = str(SELECTED_MODE).strip()

    if len(mode_str) == 2:
        if market_state == 'SIDE':
            dynamic_mode = int(mode_str[0])  # Use 1st digit for Sideways
        else:
            dynamic_mode = int(mode_str[1])  # Use 2nd digit for Trend breakouts
    else:
        try:
            dynamic_mode = int(mode_str)
        except ValueError:
            dynamic_mode = 1

    processed_df = apply_ohlc_transformation(df, mode=dynamic_mode)
    return processed_df.tail(target_rows)
