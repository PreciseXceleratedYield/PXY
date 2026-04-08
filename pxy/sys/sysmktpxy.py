# ==================================================
# sysmktpxy.py  (SINGLE RUN - NO LOOP)
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
# TradingView HA Calculation
# ------------------------------
def apply_heikin_ashi(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # HA Close (same as yours)
    df['ha_close'] = (df['Open'] + df['High'] + df['Low'] + df['Close']) / 4

    # ✅ Correct HA Open initialization (TV style)
    ha_open = [(df['Open'].iloc[0] + df['Close'].iloc[0]) / 2]

    # ✅ Recursive HA Open
    for i in range(1, len(df)):
        ha_open.append((ha_open[i-1] + df['ha_close'].iloc[i-1]) / 2)

    df['ha_open'] = ha_open

    # ✅ HA High / Low (TV standard)
    df['ha_high'] = df[['High', 'ha_open', 'ha_close']].max(axis=1)
    df['ha_low']  = df[['Low', 'ha_open', 'ha_close']].min(axis=1)

    return df


# ------------------------------
# Main Function
# ------------------------------
def get_signal():
    df = fetch_yf_data(period="5d", interval="1m")  # ✅ ensure enough history

    if df is None or len(df) < 3:
        return "NONE", "NONE"

    # ---------- APPLY HA ----------
    df = apply_heikin_ashi(df)

    # ---------- ENTRY (HA BODY) ----------
    h1 = df['ha_close'].iloc[-3] - df['ha_open'].iloc[-3]
    h2 = df['ha_close'].iloc[-2] - df['ha_open'].iloc[-2]
    h3 = df['ha_close'].iloc[-1] - df['ha_open'].iloc[-1]

    entry_signal = three_candle_signal(h1, h2, h3)

    # ---------- EXIT (RAW CLOSE) ----------
    c1 = df['Close'].iloc[-3]
    c2 = df['Close'].iloc[-2]
    c3 = df['Close'].iloc[-1]

    exit_signal = three_candle_signal(c1, c2, c3)

    return entry_signal, exit_signal


# ------------------------------
# SELF RUN (NO LOOP)
# ------------------------------
if __name__ == "__main__":
    entry_signal, exit_signal = get_signal()

    print("=== SIGNAL OUTPUT ===")
    print(f"ENTRY : {entry_signal}")
    print(f"EXIT  : {exit_signal}")
