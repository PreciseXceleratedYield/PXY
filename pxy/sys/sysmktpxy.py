# ==================================================
# SIMPLE SIGNAL ENGINE (ENTRY = EXIT SAME SIGNAL)
# ==================================================

from sysdtafpxy import fetch_yf_data
from sysdthapxy import get_ha_data


# ==================================================
# DATA FETCH
# ==================================================
def get_df():
    df = fetch_yf_data(period="5d", interval="1m")
    if df is None or len(df) < 4:
        return None
    return df


# ==================================================
# CORE SIGNAL (NO FILTERS)
# ==================================================
def entry_exit_signal(colors):

    prev = colors.iloc[-2]   # last closed candle
    curr = colors.iloc[-1]   # running candle

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

        signal = entry_exit_signal(ha_color)

        # ENTRY = EXIT SAME VALUE
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
