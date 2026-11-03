"""PXY independent entry-signal channel (IN)."""

from datetime import datetime, time as dt_time

import pandas as pd

from syscnfgpxy import (
    SYSCNFGPXY_TIMEZONE,
    SYSCNFGPXY_ENTRY_CUTOFF,
    SYSCNFGPXY_CONFIRM_AFTER,
    SYSINPXY_CONFIRM_MODE,
    SYSINPXY_SIGNAL_MODE,
)
from sysdtafpxy import fetch_yf_data
from sysexitpxy import detect_raw_direction
from sysdthapxy import get_close_direction_series, transform_dtha_ohlc, get_tsst_states


def get_signal(df=None):
    """Return the pure DTHA IN state."""
    try:
        # IN must remain inactive through 09:17:00 IST.
        now_time = datetime.now(SYSCNFGPXY_TIMEZONE).time()
        if now_time <= dt_time(9, 17) or now_time >= SYSCNFGPXY_ENTRY_CUTOFF:
            return "NONE"

        if df is None:
            df = fetch_yf_data()
        if df is None or df.empty or "Close" not in df.columns:
            return "NONE"

        if SYSINPXY_SIGNAL_MODE == "TSST":
            states = get_tsst_states(df)
            if states.empty:
                return "NONE"
            current = states.iloc[-1]
            if current == "BULL":
                return "BUY"
            if current == "BEAR":
                return "SELL"
            if current == "SIDE":
                # Contrarian Mullu entry only when TSST is SIDE.
                _, raw_direction = detect_raw_direction(df)
                return {"UP": "SELL", "DOWN": "BUY"}.get(raw_direction, "NONE")
            return "NONE"

        transformed = transform_dtha_ohlc(df)
        closes = pd.to_numeric(transformed["Close"], errors="coerce")
        # Live before 10:00 IST; completed candles only from 10:00 onward.
        if datetime.now(SYSCNFGPXY_TIMEZONE).time() >= SYSCNFGPXY_CONFIRM_AFTER:
            closes = closes.iloc[:-1]

        # C0 needs C1, and C1 needs C2, to establish both candle colours.
        if len(closes) < 3:
            return "NONE"

        directions = get_close_direction_series(closes)
        c1_direction = directions.iloc[-2]
        c0_direction = directions.iloc[-1]
        if c1_direction not in {"UP", "DOWN"} or c0_direction not in {"UP", "DOWN"}:
            return "NONE"

        if c1_direction == "DOWN" and c0_direction == "UP":
            return "BUY"
        if c1_direction == "UP" and c0_direction == "DOWN":
            return "SELL"
        return "NONE"
    except Exception:
        return "NONE"


if __name__ == "__main__":
    print(f"IN SIGNAL: {get_signal()}")

def get_entry_signal(df=None):
    """Translate pure IN state into BUY, SELL, or NONE."""
    signal = get_signal(df)
    return {
        "BUY": "BUY",
        "SELL": "SELL",
    }.get(signal, "NONE")
