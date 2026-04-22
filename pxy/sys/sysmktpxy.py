# ==================================================
# sysmktpxy.py (FINAL: MARKET INTELLIGENCE ENGINE)
# ==================================================

import pandas as pd
from sysdtafpxy import fetch_yf_data


# ==================================================
# HEIKIN ASHI
# ==================================================
def compute_heikin_ashi(df):
    ha = df.copy()

    ha_close = (df['Open'] + df['High'] + df['Low'] + df['Close']) / 4

    ha_open = [0] * len(df)
    ha_open[0] = (df['Open'].iloc[0] + df['Close'].iloc[0]) / 2

    for i in range(1, len(df)):
        ha_open[i] = (ha_open[i - 1] + ha_close.iloc[i - 1]) / 2

    ha['HA_Open'] = ha_open
    ha['HA_Close'] = ha_close

    return ha


# ==================================================
# CORE SIGNAL ENGINE
# ==================================================
def get_signal():

    df = fetch_yf_data()

    if df is None or len(df) < 10:
        return "NONE", "NONE", 0, 0, 0, None, None

    # ------------------------------
    # HA CALCULATION
    # ------------------------------
    ha = compute_heikin_ashi(df)

    # ------------------------------
    # RUNNING + CLOSED CANDLES
    # ------------------------------
    o1, o2 = ha['HA_Open'].iloc[-2], ha['HA_Open'].iloc[-1]
    c1, c2 = ha['HA_Close'].iloc[-2], ha['HA_Close'].iloc[-1]

    # ------------------------------
    # CE / PE DEPTH LOGIC
    # ------------------------------
    ce = 0
    pe = 0
    last_opp = 0

    if c2 > o2:
        ce += 1
        last_opp = pe
    else:
        pe += 1
        last_opp = ce

    # simple streak extension (you can upgrade later)
    if len(ha) > 2:
        for i in range(-5, 0):
            if abs(i) <= len(ha):
                if ha['HA_Close'].iloc[i] > ha['HA_Open'].iloc[i]:
                    ce += 1
                else:
                    pe += 1

    # ------------------------------
    # ENTRY SIGNAL
    # ------------------------------
    if c2 > o2 and c1 <= o1:
        entry_signal = "BUY"
    elif c2 < o2 and c1 >= o1:
        entry_signal = "SELL"
    elif c2 > c1:
        entry_signal = "BULL"
    elif c2 < c1:
        entry_signal = "BEAR"
    else:
        entry_signal = "NONE"

    # ------------------------------
    # EXIT SIGNAL (mirror logic)
    # ------------------------------
    if entry_signal in ["BUY", "BULL"]:
        exit_signal = "SELL"
    elif entry_signal in ["SELL", "BEAR"]:
        exit_signal = "BUY"
    else:
        exit_signal = "NONE"

    # ------------------------------
    # RETURN CONTRACT (CRITICAL)
    # ------------------------------
    return entry_signal, exit_signal, ce, pe, last_opp, df, ha
