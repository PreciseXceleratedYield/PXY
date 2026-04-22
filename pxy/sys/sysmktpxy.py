# ==================================================
# PRO SIGNAL ENGINE (HA + RUNNING CANDLE VERSION)
# ==================================================

from sysdtafpxy import fetch_yf_data


# ==================================================
# DATA
# ==================================================
def get_df():
    df = fetch_yf_data(period="5d", interval="1m")
    if df is None or len(df) < 4:
        return None
    return df


# ==================================================
# TREND STATE
# ==================================================
def trend_state(colors):

    recent = colors.dropna().iloc[-6:]  # include running influence

    green = sum(recent == "green")
    red = sum(recent == "red")

    if green > red:
        return "BULL"
    elif red > green:
        return "BEAR"
    return "SIDEWAYS"


# ==================================================
# ENTRY SIGNAL (USES RUNNING CANDLE)
# ==================================================
def entry_signal(colors):

    prev = colors.iloc[-2]   # last closed
    curr = colors.iloc[-1]   # 🔥 RUNNING CANDLE

    # 🔥 fast reaction logic
    if prev == "red" and curr == "green":
        return "BUY"

    if prev == "green" and curr == "red":
        return "SELL"

    # 🔥 continuation based on live pressure
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
            return "BEAR", "BEAR"

        from sysdthapxy import get_ha_data

        _, _, ha_color, df = get_ha_data(df=df)

        if ha_color is None:
            return "BEAR", "BEAR"

        # ==============================
        # SIGNALS (RUNNING INCLUDED)
        # ==============================
        entry = entry_signal(ha_color)
        trend = trend_state(ha_color)

        # ==============================
        # ALIGNMENT RULE
        # ==============================
        if trend == "BULL" and entry == "BUY":
            entry = "BUY"

        if trend == "BEAR" and entry == "SELL":
            entry = "SELL"

        return entry, trend

    except Exception as e:
        print("[ERROR]", e)
        return "BEAR", "BEAR"


# ==================================================
# RUN
# ==================================================
if __name__ == "__main__":
    e, t = get_signal()
    print(e, t)
