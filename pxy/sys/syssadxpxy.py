# ==================================================
# sysadxpxy.py (FIXED + PRODUCTION ADX)
# ==================================================

import pandas as pd


def calculate_adx(df: pd.DataFrame, period=14) -> float:
    """
    Proper ADX using Wilder smoothing.
    Returns latest ADX value or None if not ready.
    """

    # ------------------------------
    # BASIC CHECK
    # ------------------------------
    if df is None or len(df) < period * 2:
        return None   # ✅ NOT 0

    high = df['High']
    low = df['Low']
    close = df['Close']

    # ------------------------------
    # TRUE RANGE
    # ------------------------------
    prev_close = close.shift(1)

    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs()
    ], axis=1).max(axis=1)

    # ------------------------------
    # DIRECTIONAL MOVEMENT
    # ------------------------------
    up_move = high.diff()
    down_move = -low.diff()

    plus_dm = up_move.where((up_move > down_move) & (up_move > 0), 0.0)
    minus_dm = down_move.where((down_move > up_move) & (down_move > 0), 0.0)

    # ------------------------------
    # WILDER SMOOTHING (KEY FIX)
    # ------------------------------
    atr = tr.ewm(alpha=1/period, adjust=False).mean()
    plus_dm_smooth = plus_dm.ewm(alpha=1/period, adjust=False).mean()
    minus_dm_smooth = minus_dm.ewm(alpha=1/period, adjust=False).mean()

    # ------------------------------
    # DI
    # ------------------------------
    plus_di = 100 * (plus_dm_smooth / atr)
    minus_di = 100 * (minus_dm_smooth / atr)

    # ------------------------------
    # DX
    # ------------------------------
    dx = (plus_di - minus_di).abs() / (plus_di + minus_di) * 100

    # ------------------------------
    # ADX
    # ------------------------------
    adx = dx.ewm(alpha=1/period, adjust=False).mean()

    last_adx = adx.iloc[-1]

    # ------------------------------
    # FINAL SAFETY
    # ------------------------------
    if pd.isna(last_adx):
        return None   # ✅ DO NOT FAKE ZERO

    return float(last_adx)
