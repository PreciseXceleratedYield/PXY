"""Confirmed swing-structure break and direction (independent of BOS/IN/OUT)."""

import pandas as pd

from sysdtafpxy import fetch_yf_data
from sysdthapxy import transform_dtha_ohlc

SWING_BARS = 2


def get_structure_direction(df=None, swing_bars=SWING_BARS):
    """Return {'break': YES/NO, 'direction': BULL/BEAR/NONE}.

    Uses confirmed swing pivots only: a pivot needs swing_bars candles
    on each side. The final row is treated as the running candle and
    cannot confirm a pivot. Breaks are tested against its live Close.
    Direction persists after the latest confirmed break.
    """
    result = {"break": "NO", "direction": "NONE"}
    try:
        if df is None:
            df = fetch_yf_data()
        if df is None or df.empty or not {"High", "Low", "Close"}.issubset(df.columns):
            return result
        if not isinstance(swing_bars, int) or isinstance(swing_bars, bool) or swing_bars < 1:
            return result

        df = transform_dtha_ohlc(df)
        highs = pd.to_numeric(df["High"], errors="coerce").tolist()
        lows = pd.to_numeric(df["Low"], errors="coerce").tolist()
        closes = pd.to_numeric(df["Close"], errors="coerce").tolist()
        n = len(closes)
        if n < 2 * swing_bars + 3:
            return result

        last_high = None
        last_low = None
        direction = "NONE"
        previous_close = None
        last_break = "NO"

        for i in range(n):
            # Pivot at j is confirmed by the completed candle i-1.
            j = i - swing_bars - 1
            if j >= swing_bars:
                left = j - swing_bars
                right = j + swing_bars + 1
                h = highs[j]
                l = lows[j]
                if pd.notna(h) and all(pd.notna(x) for x in highs[left:right]):
                    if all(h > highs[k] for k in range(left, right) if k != j):
                        last_high = h
                if pd.notna(l) and all(pd.notna(x) for x in lows[left:right]):
                    if all(l < lows[k] for k in range(left, right) if k != j):
                        last_low = l

            close = closes[i]
            if pd.isna(close):
                previous_close = None
                continue

            crossed_up = (
                last_high is not None
                and previous_close is not None
                and previous_close <= last_high < close
            )
            crossed_down = (
                last_low is not None
                and previous_close is not None
                and previous_close >= last_low > close
            )
            event = "NO"
            if crossed_up and not crossed_down:
                direction = "BULL"
                event = "YES"
            elif crossed_down and not crossed_up:
                direction = "BEAR"
                event = "YES"

            if i == n - 1:
                last_break = event
            previous_close = close

        return {"break": last_break, "direction": direction}
    except Exception:
        return result


def get_signal(df=None):
    """Convenience alias for independent callers."""
    return get_structure_direction(df)


if __name__ == "__main__":
    print(get_structure_direction())
