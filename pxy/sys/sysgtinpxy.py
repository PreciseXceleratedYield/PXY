"""
PXY GTIN Entry Signal Pipeline

Uses the canonical DTHA signal calculation and the same running-candle
configuration. The only strategy difference is that a directional
flip returns NONE instead of generating an entry.

Entry mapping:
    DTHA BULL + continuing UP movement   -> BUY
    DTHA BEAR + continuing DOWN movement -> SELL
    UP -> DOWN flip                     -> NONE
    DOWN -> UP flip                     -> NONE
    Flat, invalid, or insufficient data  -> NONE

The existing MKT exit pipeline remains unchanged.
"""

import pandas as pd

from syscnfgpxy import SYSDTHAPXY_INCLUDE_RUNNING_CANDLE
from sysdtafpxy import fetch_yf_data
from sysdthapxy import (
    get_close_direction_series,
    get_signal_depth_analysis,
)


def get_entry_signal(df=None):
    """
    Generate a GTIN entry signal using DTHA's existing signal rules.

    Returns:
        "BUY", "SELL", or "NONE"
    """
    try:
        if df is None:
            df = fetch_yf_data()

        if df is None or df.empty or "Close" not in df.columns:
            return "NONE"

        # Reuse DTHA's canonical signal calculation.
        analysis = get_signal_depth_analysis(df)
        dtha_signal = analysis.get("signal", "NONE")

        if dtha_signal not in {"BULL", "BEAR"}:
            return "NONE"

        # Match DTHA's running-candle configuration exactly.
        closes = pd.to_numeric(df["Close"], errors="coerce")

        if SYSDTHAPXY_INCLUDE_RUNNING_CANDLE == "YES":
            evaluated_closes = closes
        else:
            evaluated_closes = closes.iloc[:-1]

        if len(evaluated_closes) < 3:
            return "NONE"

        last_three = evaluated_closes.iloc[-3:]

        if last_three.isna().any():
            return "NONE"

        # Reuse DTHA's direction calculation.
        directions = get_close_direction_series(closes)

        if SYSDTHAPXY_INCLUDE_RUNNING_CANDLE != "YES":
            directions = directions.iloc[:-1]

        if len(directions) < 2:
            return "NONE"

        previous_move = directions.iloc[-2]
        latest_move = directions.iloc[-1]

        # The only GTIN-specific strategy rule: suppress direction flips.
        is_flip = (
            previous_move == "UP" and latest_move == "DOWN"
        ) or (
            previous_move == "DOWN" and latest_move == "UP"
        )

        if is_flip:
            return "NONE"

        # Preserve DTHA's signal meaning; only translate the vocabulary.
        if dtha_signal == "BULL":
            return "BUY"

        if dtha_signal == "BEAR":
            return "SELL"

        return "NONE"

    except Exception:
        # Fail closed if data or signal processing fails.
        return "NONE"


if __name__ == "__main__":
    df = fetch_yf_data()
    print(f"GTIN ENTRY SIGNAL: {get_entry_signal(df)}")

