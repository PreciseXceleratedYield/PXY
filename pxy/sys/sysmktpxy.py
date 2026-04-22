# ==================================================
# 5-STATE DUAL ENGINE (STRICT MODE)
# HA + OC/2
# OUTPUT: BUY / SELL / BULL / BEAR / NONE
# ONLY 2 UPGRADE CONDITIONS
# ==================================================

from sysdtafpxy import fetch_yf_data
from sysdthapxy import get_ha_data
import pandas as pd


# ==================================================
# DATA FETCH
# ==================================================
def get_df():
    df = fetch_yf_data(period="5d", interval="1m")
    if df is None or len(df) < 10:
        return None
    return df


# ==================================================
# CLEAN INPUT
# ==================================================
def clean_colors(colors):
    colors = colors.astype(str).str.lower().str.strip()
    colors = colors.replace({
        "nan": None,
        "none": None,
        "": None
    })
    return colors


# ==================================================
# HA STATE (5 STATES ONLY)
# ==================================================
def entry_signal(colors):

    colors = clean_colors(colors)

    if len(colors.dropna()) < 2:
        return "NONE"

    prev = colors.iloc[-2]
    curr = colors.iloc[-1]

    if prev == "red" and curr == "green":
        return "BUY"

    if prev == "green" and curr == "red":
        return "SELL"

    if curr == "green":
        return "BULL"

    if curr == "red":
        return "BEAR"

    return "NONE"


# ==================================================
# OC/2 STATE (5 STATES ONLY - NO INTERPRETATION)
# ==================================================
def exit_signal(df):

    if df is None or len(df) < 3:
        return "NONE"

    oc2 = (df["Open"] + df["Close"]) / 2

    prev = oc2.iloc[-2]
    curr = oc2.iloc[-1]

    if abs(curr - prev) < 0.0005:
        return "NONE"

    if curr > prev:
        return "BULL"

    if curr < prev:
        return "BEAR"

    return "NONE"


# ==================================================
# UPGRADE ENGINE (ONLY 2 RULES)
# ==================================================
def apply_upgrade(ha_state, oc_state):

    if ha_state == "BULL" and oc_state == "BUY":
        return "BUY"

    if ha_state == "BEAR" and oc_state == "SELL":
        return "SELL"

    return ha_state


# ==================================================
# MASTER ENGINE
# ==================================================
def get_signal():

    try:
        df = get_df()
        if df is None:
            return "NONE", "NONE"

        _, _, ha_color, df = get_ha_data(df=df)

        if ha_color is None:
            return "NONE", "NONE"

        ha_color = pd.Series(ha_color)

        ha_state = entry_signal(ha_color)
        oc_state = exit_signal(df)

        final_state = apply_upgrade(ha_state, oc_state)

        return final_state, oc_state

    except Exception as e:
        print("[ERROR]", e)
        return "NONE", "NONE"


# ==================================================
# RUN
# ==================================================
if __name__ == "__main__":
    entry, exit_ = get_signal()
    print("FINAL STATE:", entry)
    print("OC/2 STATE  :", exit_)
