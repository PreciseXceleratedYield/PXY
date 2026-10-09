# pxy_engine.py
import pandas as pd
import numpy as np
from syscnfgpxy import SYSDTHAPXY_INCLUDE_RUNNING_CANDLE, SYSDPTPXY_LAST_N
from sysdtafpxy import fetch_yf_data


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

    close_series = pd.to_numeric(df["Close"], errors="coerce")
    evaluated_closes = close_series if include_running else close_series.iloc[:-1]
    evaluated_directions = get_close_direction_series(close_series)
    directions = (
        evaluated_directions
        if include_running
        else evaluated_directions.iloc[:-1]
    ).tolist()
    closes = evaluated_closes
    signal = "NONE"

    if len(closes) >= 3:
        first_move, second_move = directions[-2:]
        if first_move == "DOWN" and second_move == "UP":
            signal = "BUY"
        elif first_move == "UP" and second_move == "DOWN":
            signal = "SELL"
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
    Processes raw market OHLC candles.
    Accepts an active live_tick dictionary to update the running candle in real-time.
    Colors candles based on running Close vs the previous candle's static Close.
    """
    if df is None:
        df = fetch_yf_data()
        
    if df is None or df.empty:
        return None, None, None, pd.DataFrame()
        
    # Safeguard: Separate processing safely from global reference memory
    df = df.copy()
    
    required_cols = ['Open', 'High', 'Low', 'Close']
    for col in required_cols:
        if col not in df.columns:
            return None, None, None, pd.DataFrame()

    # 🚨 LIVE TICK INJECTION: Mutate the running candle row with raw streaming market data
    if live_tick is not None:
        last_idx = df.index[-1]
        df.loc[last_idx, 'Open'] = live_tick['Open']
        df.loc[last_idx, 'High'] = max(live_tick['High'], live_tick['Close'])
        df.loc[last_idx, 'Low'] = min(live_tick['Low'], live_tick['Close'])
        df.loc[last_idx, 'Close'] = live_tick['Close']  # Real-time ticking price

    # ==================================================
    # 🕯️ BUILD RAW MARKET RUNNING DATAFRAME
    # ==================================================
    custom_df = pd.DataFrame(index=df.index)
    custom_df['Open'] = df['Open'].values
    custom_df['High'] = df['High'].values
    custom_df['Low'] = df['Low'].values
    custom_df['Close'] = df['Close'].values
    custom_df["pxy_direction"] = get_close_direction_series(custom_df["Close"])

    custom_df["pxy_color"] = custom_df["pxy_direction"].map(
        {"UP": "green", "DOWN": "red", "FLAT": "flat"}
    ).fillna("flat")
    if custom_df["pxy_direction"].iloc[0] == "UNKNOWN":
        first_change = custom_df["Close"].iloc[0] - custom_df["Open"].iloc[0]
        first_color = "green" if first_change > 0 else "red" if first_change < 0 else "flat"
        custom_df.iloc[0, custom_df.columns.get_loc("pxy_color")] = first_color

    # ==================================================
    # 🛡️ PRODUCTION OUTPUT FILTER (SAME SIGNATURE PASSTHROUGH)
    # ==================================================
    final_df = custom_df.copy()
    pxy_close = final_df['Close'].copy()  
    pxy_open = final_df['Open'].copy()    
    pxy_color_series = final_df['pxy_color'].copy()
    
    return pxy_close, pxy_open, pxy_color_series, final_df
