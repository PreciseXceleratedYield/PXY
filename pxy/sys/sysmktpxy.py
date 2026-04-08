# ==================================================
# sysmktpxy.py  (FINAL - NO LOOP + OHLC/4 SYSTEM)
# ==================================================

import pandas as pd
from sysdtafpxy import fetch_yf_data


# ------------------------------
# Core 3-candle logic
# ------------------------------
def three_candle_signal(c1, c2, c3):
    if c2 < c1 and c2 < c3:
        return "BUY"

    elif c2 > c1 and c2 > c3:
        return "SELL"

    elif c1 < c2 < c3:
        return "BULL"

    elif c1 > c2 > c3:
        return "BEAR"

    else:
        return "NONE"


# ------------------------------
# Main Function
# ------------------------------
def get_signal():
    df = fetch_yf_data(period="5d", interval="1m")

    if df is None or len(df) < 3:
        return "NONE", "NONE"

    # ---------- ENTRY (OHLC/4 PRICE) ----------
    df['price'] = (df['Open'] + df['High'] + df['Low'] + df['Close']) / 4

    p1 = df['price'].iloc[-3]
    p2 = df['price'].iloc[-2]
    p3 = df['price'].iloc[-1]

    entry_signal = three_candle_signal(p1, p2, p3)

    # ---------- EXIT (RAW CLOSE) ----------
    c1 = df['Close'].iloc[-3]
    c2 = df['Close'].iloc[-2]
    c3 = df['Close'].iloc[-1]

    exit_signal = three_candle_signal(c1, c2, c3)

    return entry_signal, exit_signal


# ------------------------------
# SELF RUN (NO LOOP + DEBUG)
# ------------------------------
if __name__ == "__main__":
    df = fetch_yf_data(period="5d", interval="1m")

    if df is None or len(df) < 10:
        print("Not enough data")
        exit()

    # ---------- OHLC/4 PRICE ----------
    df['price'] = (df['Open'] + df['High'] + df['Low'] + df['Close']) / 4

    # Debug columns
    df['candle_body'] = df['Close'] - df['Open']

    debug_cols = [
        'Open', 'High', 'Low', 'Close',
        'price', 'candle_body'
    ]

    # 🔥 Print last 10 candles (10 mins)
    print("\n=== LAST 10 MIN DATA (DEBUG) ===")
    print(df[debug_cols].tail(10).round(2))

    # Signals
    entry_signal, exit_signal = get_signal()

    print("\n=== SIGNAL OUTPUT ===")
    print(f"ENTRY : {entry_signal}")
    print(f"EXIT  : {exit_signal}")
