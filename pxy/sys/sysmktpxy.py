# ==================================================
# sysmktpxy.py  (SINGLE RUN - NO LOOP + MID PRICE)
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

    # ---------- ENTRY (MID PRICE) ----------
    df['mid_price'] = (df['Open'] + df['Close']) / 2

    m1 = df['mid_price'].iloc[-3]
    m2 = df['mid_price'].iloc[-2]
    m3 = df['mid_price'].iloc[-1]

    entry_signal = three_candle_signal(m1, m2, m3)

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

    # ---------- MID PRICE ----------
    df['mid_price'] = (df['Open'] + df['Close']) / 2

    # Debug columns
    df['candle_body'] = df['Close'] - df['Open']

    debug_cols = [
        'Open', 'High', 'Low', 'Close',
        'mid_price', 'candle_body'
    ]

    # 🔥 Print last 10 candles (10 mins)
    print("\n=== LAST 10 MIN DATA (DEBUG) ===")
    print(df[debug_cols].tail(10).round(2))

    # Signals
    entry_signal, exit_signal = get_signal()

    print("\n=== SIGNAL OUTPUT ===")
    print(f"ENTRY : {entry_signal}")
    print(f"EXIT  : {exit_signal}")
