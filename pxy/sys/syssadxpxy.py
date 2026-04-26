# ==================================================
# sysadxpxy.py (FINAL: CLEAR DOMINANCE FORCE ENGINE)
# ==================================================

import pandas as pd


def calculate_adx(df: pd.DataFrame, period=14):
    """
    Returns:
        ce_force, pe_force

    Logic:
    - Only boost when there is CLEAR dominance
    - AND ADX is rising (acceleration)
    - Else both = 1
    """

    # ------------------------------
    # BASIC CHECK
    # ------------------------------
    if df is None or len(df) < period * 2:
        return None

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
    # WILDER SMOOTHING
    # ------------------------------
    atr = tr.ewm(alpha=1/period, adjust=False).mean()
    atr_safe = atr.replace(0, 1e-10)

    plus_dm_smooth = plus_dm.ewm(alpha=1/period, adjust=False).mean()
    minus_dm_smooth = minus_dm.ewm(alpha=1/period, adjust=False).mean()

    # ------------------------------
    # DI
    # ------------------------------
    plus_di = 100 * (plus_dm_smooth / atr_safe)
    minus_di = 100 * (minus_dm_smooth / atr_safe)

    # ------------------------------
    # DX
    # ------------------------------
    denom = (plus_di + minus_di).replace(0, 1e-10)
    dx = (plus_di - minus_di).abs() / denom * 100

    # ------------------------------
    # ADX
    # ------------------------------
    adx = dx.ewm(alpha=1/period, adjust=False).mean()

    last_adx = adx.iloc[-1]
    prev_adx = adx.iloc[-2] if len(adx) > 1 else last_adx

    last_plus_di = plus_di.iloc[-1]
    last_minus_di = minus_di.iloc[-1]

    # ------------------------------
    # FINAL SAFETY
    # ------------------------------
    if pd.isna(last_adx):
        return None

    # ==================================================
    # FORCE LOGIC (YOUR FINAL RULE)
    # ==================================================
    ce_force = 1.0
    pe_force = 1.0

    # ---- PARAMETERS (tune if needed) ----
    dominance_threshold = 3.0   # DI gap needed
    adx_min = 20.0              # ignore weak trends
    accel_delta = 0.5           # avoid micro noise

    di_diff = last_plus_di - last_minus_di

    accelerating = (last_adx - prev_adx) > accel_delta
    strong_trend = last_adx > adx_min

    if accelerating and strong_trend:

        # ------------------ BULL DOMINANCE ------------------
        if di_diff > dominance_threshold:
            boost = 1 + max(0, (last_adx - 20) / 50)
            ce_force = min(boost, 1.8)

        # ------------------ BEAR DOMINANCE ------------------
        elif di_diff < -dominance_threshold:
            boost = 1 + max(0, (last_adx - 20) / 50)
            pe_force = min(boost, 1.8)

    return ce_force, pe_force


# ==================================================
# TEST BLOCK (REAL RUN)
# ==================================================
if __name__ == "__main__":

    import yfinance as yf

    symbol = "^NSEI"   # change if needed

    df = yf.download(symbol, interval="5m", period="5d", progress=False)

    result = calculate_adx(df)

    if result:
        ce, pe = result
        print("\nFORCE OUTPUT")
        print(f"CE FORCE : {ce:.2f}")
        print(f"PE FORCE : {pe:.2f}")
    else:
        print("NOT READY")
