# sysadxpxy.py
import pandas as pd
from sysdtafpxy import fetch_yf_data  # <-- always use config symbol

# -------------------- ADX Calculation --------------------
def calculate_adx(df: pd.DataFrame, period=14) -> float:
    """
    Calculate ADX (Average Directional Index) for trend strength.
    Returns latest ADX value.
    """
    if df is None or len(df) < period + 1:
        return 0.0

    high = df['High']
    low = df['Low']
    close = df['Close']

    # True Range (TR)
    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs()
    ], axis=1).max(axis=1)

    # Directional Movements
    up_move = high - high.shift(1)
    down_move = low.shift(1) - low
    plus_dm = up_move.where((up_move > down_move) & (up_move > 0), 0.0)
    minus_dm = down_move.where((down_move > up_move) & (down_move > 0), 0.0)

    # Smooth TR and DMs
    atr = tr.rolling(period).mean()
    plus_di = 100 * (plus_dm.rolling(period).sum() / atr)
    minus_di = 100 * (minus_dm.rolling(period).sum() / atr)

    # DX and ADX
    dx = (plus_di - minus_di).abs() / (plus_di + minus_di) * 100
    adx = dx.rolling(period).mean()

    return adx.iloc[-1] if not pd.isna(adx.iloc[-1]) else 0.0


# -------------------- Self-runnable test --------------------
if __name__ == "__main__":
    print("=== ADX Module Test ===")
    df = fetch_yf_data(period="5d", interval="1m")  # 1-min Nifty data
    if df is None or df.empty:
        print("No data available for ADX calculation")
    else:
        df = df[['Open', 'High', 'Low', 'Close']]  # only OHLC needed
        adx_val = calculate_adx(df)
        print(f"Latest ADX: {adx_val:.2f}")
