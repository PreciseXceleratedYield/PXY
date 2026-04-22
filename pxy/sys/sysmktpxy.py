# ==================================================
# SIMPLE PRO SIGNAL ENGINE (PURE HEIKIN-ASHI STATE)
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
# TREND STATE (BULL / BEAR)
# ==================================================
def trend_state(colors):

    recent = colors.dropna().iloc[-5:]

    green = sum(recent == "green")
    red = sum(recent == "red")

    if green > red:
        return "BULL"
    elif red > green:
        return "BEAR"
    return "SIDEWAYS"


# ==================================================
# ENTRY SIGNAL (BUY / SELL)
# ==================================================
def entry_signal(colors):

    prev = colors.iloc[-3]   # closed candle
    curr = colors.iloc[-2]   # last closed candle

    if prev == "red" and curr == "green":
        return "BUY"

    if prev == "green" and curr == "red":
        return "SELL"

    if curr == "green":
        return "BULL"

    if curr == "red":
        return "BEAR"

    return "BEAR"


# ==================================================
# MASTER ENGINE
# ==================================================
def get_signal():

    try:
        df = get_df()
        if df is None:
            return "BEAR", "BEAR"

        # 🔥 IMPORT HA ENGINE
        from sysdthapxy import get_ha_data

        _, _, ha_color, df = get_ha_data(df=df)

        if ha_color is None:
            return "BEAR", "BEAR"

        # ==============================
        # SIGNALS FROM COLOR ONLY
        # ==============================
        entry = entry_signal(ha_color)
        trend = trend_state(ha_color)

        # ==============================
        # ALIGNMENT RULE (SIMPLE)
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
