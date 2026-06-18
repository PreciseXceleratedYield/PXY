"""
===============================================================================
PXY OPTION ROUTING ENGINE: EXCLUSIVE SYMMETRIC TREND ROUTER (ATM / ATM)
===============================================================================
Operational Matrix (Strictly Blueprint Table Synced):
- SUPER: BULL -> ENTRY: BULL     | EXIT: BULL
- SUPER: BEAR -> ENTRY: BEAR     | EXIT: BEAR
- SUPER: SELL -> ENTRY: ATMSELL  | SELL
- SUPER: BUY  -> ENTRY: ATMBUY   | BUY
===============================================================================
"""

import numpy as np
import pandas as pd
import yfinance as yf


def get_entry_signal(df=None, symbol="^NSEI", period=1, factor=1.0):
    """Calculates normal, industry-standard Supertrend using close-price confirmation.

    Matches standard charts out-of-the-box.
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

    # Case-insensitive column verification
    col_mapping = {col.lower(): col for col in df.columns}
    for req in ["high", "low", "close"]:
        if req not in col_mapping:
            return "NONE", "NONE"

    high = df[col_mapping["high"]].values
    low = df[col_mapping["low"]].values
    close = df[col_mapping["close"]].values

    # 2. CALCULATE STANDARD ATR (1-PERIOD)
    prev_close = np.roll(close, 1)
    prev_close[0] = close[0]

    tr1 = high - low
    tr2 = np.abs(high - prev_close)
    tr3 = np.abs(low - prev_close)
    tr = np.maximum(tr1, np.maximum(tr2, tr3))

    # Calculate rolling mean (ATR) using standard pandas rolling windows
    atr = pd.Series(tr).rolling(window=period, min_periods=1).mean().values

    # 3. CLASSIC SUPERTREND CALCULATION ENGINE
    hl2 = (high + low) / 2
    basic_upper = hl2 + (factor * atr)
    basic_lower = hl2 - (factor * atr)

    upper_band = np.zeros(len(df))
    lower_band = np.zeros(len(df))
    trend = np.ones(len(df))  # 1 for Green/Buy, -1 for Red/Sell

    for i in range(len(df)):
        if i == 0:
            upper_band[i] = basic_upper[i]
            lower_band[i] = basic_lower[i]
            continue

        # Normal Supertrend trailing band calculations
        if basic_upper[i] < upper_band[i - 1] or close[i - 1] > upper_band[i - 1]:
            upper_band[i] = basic_upper[i]
        else:
            upper_band[i] = upper_band[i - 1]

        if basic_lower[i] > lower_band[i - 1] or close[i - 1] < lower_band[i - 1]:
            lower_band[i] = basic_lower[i]
        else:
            lower_band[i] = lower_band[i - 1]

        # Normal trend direction switch using candle confirmation (Close Price)
        if close[i] > upper_band[i]:
            trend[i] = 1
        elif close[i] < lower_band[i]:
            trend[i] = -1
        else:
            trend[i] = trend[i - 1]

    # Map numbers back to operational string matrix rules
    super_state = "BUY" if trend[-1] == 1 else "SELL"

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

