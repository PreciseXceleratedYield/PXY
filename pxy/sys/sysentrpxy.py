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


def get_entry_signal(df=None, symbol="^NSEI", period=1, factor=1.0):
    """Calculates ATR & Supertrend inline using instantaneous touch confirmation

    instead of waiting for candle close.
    """
    # 1. ENFORCE COMPATIBILITY: CHECK IF THE FIRST ARGUMENT IS A DATAFRAME OR SYMBOL
    if isinstance(df, str):
        symbol = df
        df = None

    if df is None:
        df = yf.download(symbol, period="5d", interval="1m", progress=False)

    if df is None or df.empty:
        return "NONE", "NONE"

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [col for col in df.columns]

    df = df.copy()

    # Ensure required columns are present and case-insensitive
    col_mapping = {col.lower(): col for col in df.columns}
    for req in ["high", "low", "close"]:
        if req not in col_mapping:
            return "NONE", "NONE"

    high = df[col_mapping["high"]]
    low = df[col_mapping["low"]]
    close = df[col_mapping["close"]]
    prev_close = close.shift(1)

    # 2. CALCULATE INLINE ATR (1-PERIOD)
    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()

    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    df["ATR"] = tr.rolling(window=period).mean()

    # 3. CALCULATE INLINE SUPERTREND BANDS
    hl2 = (high + low) / 2
    df["Basic_Upper"] = hl2 + (factor * df["ATR"])
    df["Basic_Lower"] = hl2 - (factor * df["ATR"])

    upper_band = np.zeros(len(df))
    lower_band = np.zeros(len(df))
    trend = np.zeros(len(df))  # 1 for Buy/Bull, -1 for Sell/Bear

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

        # INSTANT TOUCH CONFIRMATION LOGIC
        # High touching upper band triggers buy; Low touching lower band triggers sell
        if high.iloc[i] >= upper_band[i]:
            trend[i] = 1
        elif low.iloc[i] <= lower_band[i]:
            trend[i] = -1
        else:
            trend[i] = trend[i - 1]

    # Map numbers back to operational string matrix rules
    df["Signal"] = np.where(trend == 1, "BUY", "SELL")

    last_idx = -1
    raw_sig = df["Signal"].iloc[last_idx]
    super_state = str(raw_sig).upper().strip()

    # 4. MATCH CODES ACCORDING TO THE BLUEPRINT MATRIX
    if super_state == "BULL":
        final_signal, exit_sig = "ATMBUY", "BULL"
    elif super_state == "BEAR":
        final_signal, exit_sig = "ATMSELL", "BEAR"
    elif super_state == "SELL":
        final_signal, exit_sig = "ATMSELL", "SELL"
    elif super_state == "BUY":
        final_signal, exit_sig = "ATMBUY", "BUY"
    else:
        final_signal, exit_sig = "NONE", "NONE"

    return final_signal, exit_sig


if __name__ == "__main__":
    final_route, cascaded_exit = get_entry_signal(df=None, symbol="^NSEI")
    print(f"ENTRY: {final_route} | EXIT: {cascaded_exit}")


