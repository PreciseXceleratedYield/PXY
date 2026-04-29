# ==================================================
# sysadxpxy.py (FIXED SURGICAL FORCE)
# ==================================================
import pandas as pd

def calculate_adx(df: pd.DataFrame, period=14):
    if df is None or len(df) < period * 2:
        return 1.0, 1.0  # Base point values

    high, low, close = df['High'], df['Low'], df['Close']
    prev_close = close.shift(1)

    # --- TRUE RANGE ---
    tr = pd.concat([high - low, (high - prev_close).abs(), (low - prev_close).abs()], axis=1).max(axis=1)

    # --- DIRECTIONAL MOVEMENT ---
    up_move = high.diff()
    down_move = -low.diff()
    plus_dm = up_move.where((up_move > down_move) & (up_move > 0), 0.0)
    minus_dm = down_move.where((down_move > up_move) & (down_move > 0), 0.0)

    # --- SMOOTHING ---
    atr = tr.ewm(alpha=1/period, adjust=False).mean().replace(0, 1e-10)
    plus_dm_smooth = plus_dm.ewm(alpha=1/period, adjust=False).mean()
    minus_dm_smooth = minus_dm.ewm(alpha=1/period, adjust=False).mean()

    # --- DI & ADX ---
    plus_di = 100 * (plus_dm_smooth / atr)
    minus_di = 100 * (minus_dm_smooth / atr)
    denom = (plus_di + minus_di).replace(0, 1e-10)
    dx = (plus_di - minus_di).abs() / denom * 100
    adx = dx.ewm(alpha=1/period, adjust=False).mean()

    last_adx = adx.iloc[-1]
    prev_adx = adx.iloc[-2] if len(adx) > 1 else last_adx
    last_plus_di = plus_di.iloc[-1]
    last_minus_di = minus_di.iloc[-1]

    if pd.isna(last_adx):
        return 1.0, 1.0

    # --- FORCE ENGINE ---
    ce_val = 1.0
    pe_val = 1.0
    di_diff = last_plus_di - last_minus_di
    accelerating = (last_adx - prev_adx) > 0.1 # Lowered threshold for sensitivity
    strong_trend = last_adx > 20

    if accelerating and strong_trend:
        boost = 1 + max(0, (last_adx - 20) / 50)
        if di_diff > 3:
            ce_val = min(boost, 1.99) # Ceiling check
        elif di_diff < -3:
            pe_val = min(boost, 1.99)

    # --- SURGICAL ADJUSTMENT (Value * 100 - 100) ---
    # Moved OUTSIDE the if-block so it always processes
    ce_force = round((ce_val * 100) - 100, 1)
    pe_force = round((pe_val * 100) - 100, 1)

    # Ensure minimum 1.0 point if neutral
    ce_force = max(1.0, ce_force)
    pe_force = max(1.0, pe_force)

    return ce_force, pe_force

if __name__ == "__main__":
    print("ADX FORCE MODULE LOADED OK")

