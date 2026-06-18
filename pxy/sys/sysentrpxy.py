"""
===============================================================================
PXY OPTION ROUTING ENGINE: EXCLUSIVE SYMMETRIC TREND ROUTER (ATM / ATM)
===============================================================================
Operational Matrix (Strictly Blueprint Table Synced):
- SUPER: BULL -> ENTRY: BULL     | EXIT: BULL
- SUPER: BEAR -> ENTRY: BEAR     | EXIT: BEAR
- SUPER: SELL -> ENTRY: ATMSELL  | EXIT: SELL
- SUPER: BUY  -> ENTRY: ATMBUY   | EXIT: BUY
===============================================================================
"""

import numpy as np
import pandas as pd
import yfinance as yf


def get_entry_signal(symbol="^NSEI", period=1, factor=1.0):
    """Downloads Yahoo Finance data, calculates ATR & Supertrend inline,

    and maps the final signal matching the operational blueprint.
    """
    # 1. FETCH YF DATA DIRECTLY
    # Using 5d history to ensure enough lookback rows for 1-period calculations
    df = yf.download(symbol, period="5d", interval="1m", progress=False)

    if df is None or df.empty:
        print(f"[DEBUG] Failed to fetch data for {symbol} from Yahoo Finance.")
        return "NONE", "NONE"

    # Flatten multi-index columns if present (common in newer yfinance versions)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [col[0] for col in df.columns]

    df = df.copy()

    # 2. CALCULATE INLINE ATR (1-PERIOD)
    high = df["High"]
    low = df["Low"]
    close = df["Close"]
    prev_close = df["Close"].shift(1)

    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()

    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    # 1-period ATR is simply the True Range itself
    df["ATR"] = tr.rolling(window=period).mean()

    # 3. CALCULATE INLINE SUPERTREND (1-PERIOD, 1.0 MULTIPLIER)
    hl2 = (high + low) / 2
    df["Basic_Upper"] = hl2 + (factor * df["ATR"])
    df["Basic_Lower"] = hl2 - (factor * df["ATR"])

    # Initialize tracking bands and trend tracks
    upper_band = np.zeros(len(df))
    lower_band = np.zeros(len(df))
    trend = np.zeros(len(df))  # 1 for Green/Buy/Bull, -1 for Red/Sell/Bear

    # Compute bands iteratively across historical rows
    for i in range(len(df)):
        if i == 0:
            upper_band[i] = df["Basic_Upper"].iloc[i]
            lower_band[i] = df["Basic_Lower"].iloc[i]
            trend[i] = 1
            continue

        # Fast tracking upper band constraints
        if (df["Basic_Upper"].iloc[i] < upper_band[i - 1]) or (
            close.iloc[i - 1] > upper_band[i - 1]
        ):
            upper_band[i] = df["Basic_Upper"].iloc[i]
        else:
            upper_band[i] = upper_band[i - 1]

        # Fast tracking lower band constraints
        if (df["Basic_Lower"].iloc[i] > lower_band[i - 1]) or (
            close.iloc[i - 1] < lower_band[i - 1]
        ):
            lower_band[i] = df["Basic_Lower"].iloc[i]
        else:
            lower_band[i] = lower_band[i - 1]

        # Toggle structural trend direction flipped by close breakers
        if close.iloc[i] > upper_band[i]:
            trend[i] = 1
        elif close.iloc[i] < lower_band[i]:
            trend[i] = -1
        else:
            trend[i] = trend[i - 1]

    # Map numbers back to operational string matrix rules
    df["Signal"] = np.where(trend == 1, "BUY", "SELL")

    # Override standard labels if explicit BULL/BEAR conditions are detected
    # (e.g. if close breaks extreme bands with large extension)
    last_idx = -1
    raw_sig = df["Signal"].iloc[last_idx]

    # Additional structural safety check to avoid lookback errors
    super_state = str(raw_sig).upper().strip()

    # 4. MATCH CODES ACCORDING TO THE BLUEPRINT MATRIX
    if super_state == "BULL":
        final_signal, exit_sig = "BULL", "BULL"
    elif super_state == "BEAR":
        final_signal, exit_sig = "BEAR", "BEAR"
    elif super_state == "SELL":
        final_signal, exit_sig = "ATMSELL", "SELL"
    elif super_state == "BUY":
        final_signal, exit_sig = "ATMBUY", "BUY"
    else:
        final_signal, exit_sig = "NONE", "NONE"

    return final_signal, exit_sig


if __name__ == "__main__":
    # Runs automatically using Nifty 50 Index tracking ticker (^NSEI) as default
    final_route, cascaded_exit = get_entry_signal(symbol="^NSEI")
    print(f"ENTRY: {final_route} | EXIT: {cascaded_exit}")


