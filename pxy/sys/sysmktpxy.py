# ==================================================
# SIMPLE SIGNAL ENGINE (FIXED + STABLE)
# ==================================================

from sysdtafpxy import fetch_yf_data
from sysdthapxy import get_ha_data
import pandas as pd


# ==================================================
# DATA FETCH
# ==================================================
def get_df():
    df = fetch_yf_data(period="5d", interval="1m")
    if df is None or len(df) < 4:
        return None
    return df


# ==================================================
# CLEAN COLOR NORMALIZER (🔥 FIX)
# ==================================================
def clean_colors(colors):

    colors = colors.astype(str).str.lower().str.strip()

    # fix common junk values
    colors = colors.replace({
        "nan": None,
        "none": None,
        "": None
    })

    return colors


# ==================================================
# CORE SIGNAL
# ==================================================
def entry_exit_signal(colors):

    colors = clean_colors(colors)

    # ensure we have valid last 2 candles
    if len(colors.dropna()) < 2:
        return "NONE"

    prev = colors.iloc[-2]
    curr = colors.iloc[-1]

    if prev == "red" and curr == "green":
        return "BUY"

    if prev == "green" and curr == "red":
        return "SELL"

    if prev == "green" and curr == "green":
        return "BULL"

    if prev == "red" and curr == "red":
        return "BEAR"

    return "NONE"


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

        signal = entry_exit_signal(ha_color)

        return signal, signal

    except Exception as e:
        print("[ERROR]", e)
        return "NONE", "NONE"


# ==================================================
# RUN
# ==================================================
if __name__ == "__main__":
    entry, exit_ = get_signal()
    print(entry, exit_)
