"""PXY independent entry-signal channel (IN)."""

import pandas as pd

from syscnfgpxy import (
    SYSINPXY_CONFIRM_MODE,
    SYSINPXY_SIGNAL_MODE,
)
from sysdtafpxy import fetch_yf_data
from sysdirpxy import detect_raw_direction
from sysdthapxy import get_close_direction_series, transform_dtha_ohlc, get_stmt_states, get_supr_signals, get_sdir_signals, get_stma_signals, get_pipe_binary_direction


def get_signal(df=None):
    """Return the pure DTHA IN state."""
    try:
        if df is None:
            df = fetch_yf_data()
        if df is None or df.empty or "Close" not in df.columns:
            return "NONE"

        # Live mode: include the forming candle in entry signals.

        if SYSINPXY_SIGNAL_MODE == "OC2":
            # Pure OC2: compare running midpoint against previous midpoint, no TSMA.
            if len(df) < 2 or "Open" not in df.columns:
                return "NONE"
            mid = (pd.to_numeric(df["Open"], errors="coerce") + pd.to_numeric(df["Close"], errors="coerce")) / 2.0
            previous, current = mid.iloc[-2], mid.iloc[-1]
            if pd.isna(previous) or pd.isna(current):
                return "NONE"
            signal = "BUY" if current > previous else "SELL" if current < previous else "NONE"
            if signal == "NONE":
                return "NONE"

            # SDIR qualifies OC2 signals. A fresh OC2 direction flip on C0
            # wins for that candle even when SDIR points the other way.
            from syssdirpxy import get_structure_direction
            sdir = str(get_structure_direction(df).get("direction", "NONE")).upper()
            if (signal == "BUY" and sdir == "BULL") or (signal == "SELL" and sdir == "BEAR"):
                return signal

            if len(mid) < 3 or pd.isna(mid.iloc[-3]):
                return "NONE"
            previous_signal = (
                "BUY" if mid.iloc[-2] > mid.iloc[-3]
                else "SELL" if mid.iloc[-2] < mid.iloc[-3]
                else "NONE"
            )
            return signal if previous_signal in {"BUY", "SELL"} and previous_signal != signal else "NONE"

        if SYSINPXY_SIGNAL_MODE == "SDIR":
            return get_sdir_signals(df)[0]

        if SYSINPXY_SIGNAL_MODE == "STMT":
            states = get_stmt_states(df)
            if states.empty:
                return "NONE"
            current = states.iloc[-1]
            if current == "BULL":
                return "BUY"
            if current == "BEAR":
                return "SELL"
            if current == "SIDE":
                # Contrarian Mullu entry only when STMT is SIDE.
                _, raw_direction = detect_raw_direction(df)
                return {"UP": "SELL", "DOWN": "BUY"}.get(raw_direction, "NONE")
            return "NONE"

        if SYSINPXY_SIGNAL_MODE == "PIPE":
            return {"BULL": "BUY", "BEAR": "SELL"}.get(get_pipe_binary_direction(df), "NONE")

        if SYSINPXY_SIGNAL_MODE == "SUPR":
            return get_supr_signals(df)[0]

        if SYSINPXY_SIGNAL_MODE not in {"TSMAC0", "TSMAC1"}:
            return "NONE"

        transformed = transform_dtha_ohlc(df)
        closes = pd.to_numeric(transformed["Close"], errors="coerce")
        # TSMAC0 follows the running candle directly; TSMAC1 retains the existing confirmation.
        # C2 and C1 are completed candles; C0 is the forming candle.
        if len(closes) < (2 if SYSINPXY_SIGNAL_MODE == "TSMAC0" else 4):
            return "NONE"

        directions = get_close_direction_series(closes)
        if SYSINPXY_SIGNAL_MODE == "TSMAC0":
            return {"UP": "BUY", "DOWN": "SELL"}.get(directions.iloc[-1], "NONE")
        past_completed = directions.iloc[-3]
        latest_completed = directions.iloc[-2]
        running = directions.iloc[-1]

        if (past_completed, latest_completed, running) in {
            ("DOWN", "UP", "UP"),
            ("UP", "DOWN", "UP"),  # GREEN-RED-GREEN
        }:
            return "BUY"
        if (past_completed, latest_completed, running) in {
            ("UP", "DOWN", "DOWN"),
            ("DOWN", "UP", "DOWN"),  # RED-GREEN-RED
        }:
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
