
"""
PXY GTIN Entry Signal Pipeline

Uses the running candle from the existing DTAF market-data feed.

Entry rules:
    Two consecutive rising close-to-close movements -> BUY
    Two consecutive falling close-to-close movements -> SELL
    Mixed, flat, invalid, or insufficient data -> NONE

This module is independent of the existing DTHA/MKT exit pipeline.
"""

import pandas as pd

from sysdtafpxy import fetch_yf_data


def get_entry_signal(df=None):
    """
    Generate an entry-only signal from the latest three closes.

    The final close is the running candle's current Close value.
    No candle-close confirmation is required.

    Returns:
        "BUY", "SELL", or "NONE"
    """
    try:
        if df is None:
            df = fetch_yf_data()

        if df is None or df.empty or "Close" not in df.columns:
            return "NONE"

        closes = pd.to_numeric(df["Close"], errors="coerce")

        # Three closes are required for two consecutive movements.
        if len(closes) < 3:
            return "NONE"

        last_three = closes.iloc[-3:]

        # Fail closed if any of the three consecutive closes is invalid.
        if last_three.isna().any():
            return "NONE"

        previous_close = float(last_three.iloc[0])
        middle_close = float(last_three.iloc[1])
        running_close = float(last_three.iloc[2])

        first_move = middle_close - previous_close
        second_move = running_close - middle_close

        if first_move > 0 and second_move > 0:
            return "BUY"

        if first_move < 0 and second_move < 0:
            return "SELL"

        return "NONE"

    except Exception:
        # Entry signals must fail closed on any data or processing error.
        return "NONE"


if __name__ == "__main__":
    df = fetch_yf_data()
    print(f"GTIN ENTRY SIGNAL: {get_entry_signal(df)}")
