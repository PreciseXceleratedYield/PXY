# ==================================================
# sysadxpxy.py (SAFE FORCE ENGINE - FIXED)
# ==================================================

import pandas as pd


def calculate_adx(df: pd.DataFrame, period=14):
    """
    Returns:
        ce_force (float), pe_force (float)

    Logic:
    - Uses ADX + DI direction
    - Converts trend strength into directional force
    - Safe fallback = (1.0, 1.0)
    """

    # ------------------------------
    # BASIC CHECK
    # ------------------------------
    if df is None or len(df) < period * 2:
        return 1.0, 1.0

    high = df['High']
    low = df['Low']
    close = df['Close']

    prev_close = close.shift(1)

    # ------------------------------
    # TRUE RANGE
    # ------------------------------
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
    # SMOOTHING
    # ------------------------------
    atr = tr.ewm(alpha=1/period, adjust=False).mean()
    atr = atr.replace(0, 1e-10)

    plus_dm_smooth = plus_dm.ewm(alpha=1/period, adjust=False).mean()
    minus_dm_smooth = minus_dm.ewm(alpha=1/period, adjust=False).mean()

    # ------------------------------
    # DI
    # ------------------------------
    plus_di = 100 * (plus_dm_smooth / atr)
    minus_di = 100 * (minus_dm_smooth / atr)

    denom = (plus_di + minus_di).replace(0, 1e-10)

    # ------------------------------
    # DX & ADX
    # ------------------------------
    dx = (plus_di - minus_di).abs() / denom * 100
    adx = dx.ewm(alpha=1/period, adjust=False).mean()

    last_adx = adx.iloc[-1]
    prev_adx = adx.iloc[-2] if len(adx) > 1 else last_adx

    last_plus_di = plus_di.iloc[-1]
    last_minus_di = minus_di.iloc[-1]

    # ------------------------------
    # SAFETY
    # ------------------------------
    if pd.isna(last_adx):
        return 1.0, 1.0

    # ------------------------------
    # FORCE ENGINE
    # ------------------------------
    ce_force = 1.0
    pe_force = 1.0

    di_diff = last_plus_di - last_minus_di
    accelerating = (last_adx - prev_adx) > 0.5
    strong_trend = last_adx > 20

    if accelerating and strong_trend:

        # BULLISH DOMINANCE
        if di_diff > 3:
            boost = 1 + max(0, (last_adx - 20) / 50)
            ce_force = min(boost, 1.8)

        # BEARISH DOMINANCE
        elif di_diff < -3:
            boost = 1 + max(0, (last_adx - 20) / 50)
            pe_force = min(boost, 1.8)

    return ce_force, pe_force


# ==================================================
# TEST (OPTIONAL)
# ==================================================
if __name__ == "__main__":
    print("ADX FORCE MODULE LOADED OK")
