"""Confirmed swing-structure break and direction (independent of BOS/IN/OUT)."""

import pandas as pd

from sysdtafpxy import fetch_yf_data
from sysdthapxy import transform_dtha_ohlc

SWING_BARS = 1
MAX_LOOKBACK = 14


def get_structure_direction(df=None, swing_bars=SWING_BARS):
    """Return {'break': YES/NO, 'direction': BULL/BEAR/NONE}.

    Uses confirmed swing pivots only: a pivot needs swing_bars candles
    on each side. The final row is treated as the running candle and
    cannot confirm a pivot. Breaks are confirmed only by completed candle closes; the running candle is ignored.
    Swing levels expire after 14 candles. New confirmed three-pivot microtrends
    may change direction when no breakout occurs; otherwise retain direction.
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

        last_high = None  # (price, pivot_index)
        last_low = None   # (price, pivot_index)
        direction = "NONE"
        previous_close = None
        last_break = "NO"
        pivots = []  # Confirmed, chronological (kind, price, index) swings

        # Exclude the final, still-forming candle from breakout confirmation.
        for i in range(n - 1):
            # Pivot at j is confirmed by the completed candle i-1.
            j = i - swing_bars - 1
            # Only pivots fully contained in the latest 14-candle window qualify.
            new_pivots = []
            if j >= swing_bars and j - swing_bars >= max(0, i - MAX_LOOKBACK + 1):
                left = j - swing_bars
                right = j + swing_bars + 1
                h = highs[j]
                l = lows[j]
                if pd.notna(h) and all(pd.notna(x) for x in highs[left:right]):
                    if all(h > highs[k] for k in range(left, right) if k != j):
                        last_high = (h, j)
                        new_pivots.append(("H", h, j))
                if pd.notna(l) and all(pd.notna(x) for x in lows[left:right]):
                    if all(l < lows[k] for k in range(left, right) if k != j):
                        last_low = (l, j)
                        new_pivots.append(("L", l, j))

            # Expire obsolete swing levels, but preserve the last confirmed direction.
            if last_high is not None and last_high[1] < i - MAX_LOOKBACK + 1:
                last_high = None
            if last_low is not None and last_low[1] < i - MAX_LOOKBACK + 1:
                last_low = None
            # Keep only recent confirmed swing points. A newly confirmed
            # pivot can produce an early three-point microtrend signal.
            pivots = [p for p in pivots if p[2] >= i - MAX_LOOKBACK + 1]
            for pivot in new_pivots:
                if pivots and pivots[-1][0] == pivot[0]:
                    # Preserve the more extreme point in a same-kind run.
                    old = pivots[-1]
                    if (pivot[0] == "H" and pivot[1] > old[1]) or (pivot[0] == "L" and pivot[1] < old[1]):
                        pivots[-1] = pivot
                else:
                    pivots.append(pivot)
            microtrend = None
            if new_pivots and len(pivots) >= 3:
                a, b, c = pivots[-3:]
                if (a[0], b[0], c[0]) == ("L", "H", "L") and c[1] > a[1]:
                    microtrend = "BULL"
                elif (a[0], b[0], c[0]) == ("H", "L", "H") and c[1] < a[1]:
                    microtrend = "BEAR"
            close = closes[i]
            if pd.isna(close):
                previous_close = None
                continue

            crossed_up = (
                last_high is not None
                and previous_close is not None
                and previous_close <= last_high[0] < close
            )
            crossed_down = (
                last_low is not None
                and previous_close is not None
                and previous_close >= last_low[0] > close
            )
            event = "NO"
            if crossed_up and not crossed_down:
                direction = "BULL"
                event = "YES"
            elif crossed_down and not crossed_up:
                direction = "BEAR"
                event = "YES"
            elif microtrend is not None:
                # Breakout always wins; microtrend updates only on a newly
                # confirmed three-point pattern, not on every subsequent bar.
                direction = microtrend

            if i == n - 2:
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
