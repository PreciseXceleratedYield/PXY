# ==================================================
# PRO SIGNAL ENGINE (FAIL-SAFE HA VERSION)
# ==================================================

from sysdtafpxy import fetch_yf_data

# ==================================================
# GLOBAL SWITCHES
# ==================================================
MODE = "HKIN"   # "OC2" or "HKIN"
DEBUG = False
EXIT_MODE = "C"


# ==================================================
# DEBUG LOGGER
# ==================================================
def dbg(*args):
    if DEBUG:
        print("[DBG]", *args)


# ==================================================
# DATA LOADER
# ==================================================
def get_df():
    df = fetch_yf_data(period="5d", interval="1m")

    if df is None or len(df) < 4:
        return None

    return df


# ==================================================
# SIGNAL FUNCTIONS
# ==================================================
def three_candle_signal(c1, c2, c3):

    if c2 < c1 and c2 < c3:
        return "BUY"
    if c2 > c1 and c2 > c3:
        return "SELL"
    if c1 < c2 < c3:
        return "BULL"
    if c1 > c2 > c3:
        return "BEAR"

    return "NONE"


def four_candle_signal(c0, c1, c2, c3):

    if c1 == min([c0, c1, c2, c3]):
        return "BUY"
    if c1 == max([c0, c1, c2, c3]):
        return "SELL"
    if c3 > c2 > c1 > c0:
        return "BULL"
    if c3 < c2 < c1 < c0:
        return "BEAR"

    return "NONE"


def momentum_signal(c2, c3):

    if c3 > c2:
        return "BULL"
    if c3 < c2:
        return "BEAR"

    return "NONE"


# ==================================================
# HKIN ENTRY ENGINE (STATE BASED)
# ==================================================
def hkin_state(prev_o, prev_c, curr_o, curr_c):

    prev_green = prev_c > prev_o
    curr_green = curr_c > curr_o

    if (not prev_green) and curr_green:
        return "BUY"

    if prev_green and (not curr_green):
        return "SELL"

    if curr_green and prev_green:
        return "BULL"

    if (not curr_green) and (not prev_green):
        return "BEAR"

    return "BULL"


# ==================================================
# MASTER ENGINE
# ==================================================
def get_signal():

    try:
        df = get_df()

        if df is None:
            return "BEAR", "BEAR"

        # ==============================
        # OC2 MODE
        # ==============================
        if MODE == "OC2":

            price = (df['Open'] + df['Close']) / 2
            p0, p1, p2, p3 = price.iloc[-4], price.iloc[-3], price.iloc[-2], price.iloc[-1]

            entry_signal = three_candle_signal(p1, p2, p3)

            if entry_signal == "NONE":
                entry_signal = four_candle_signal(p0, p1, p2, p3)

            if entry_signal == "NONE":
                entry_signal = momentum_signal(p2, p3)

        # ==============================
        # HKIN MODE (SAFE + FAIL-SAFE)
        # ==============================
        else:

            from sysdthapxy import get_ha_data

            result = get_ha_data(df=df)

            if result is None:
                return "BEAR", "BEAR"

            _, _, _, df = result

            # 🔥 HARD SAFETY CHECK
            if df is None or "HA_Open" not in df.columns or "HA_Close" not in df.columns:
                return "BEAR", "BEAR"

            # 🔥 ONLY CLOSED CANDLES (-3, -2)
            prev_o = df["HA_Open"].iloc[-3]
            prev_c = df["HA_Close"].iloc[-3]

            curr_o = df["HA_Open"].iloc[-2]
            curr_c = df["HA_Close"].iloc[-2]

            entry_signal = hkin_state(prev_o, prev_c, curr_o, curr_c)

        # ==============================
        # EXIT ENGINE (CLOSE BASED)
        # ==============================
        if EXIT_MODE == "C":

            c0, c1, c2, c3 = (
                df['Close'].iloc[-4],
                df['Close'].iloc[-3],
                df['Close'].iloc[-2],
                df['Close'].iloc[-1]
            )

            exit_signal = three_candle_signal(c1, c2, c3)

            if exit_signal == "NONE":
                exit_signal = four_candle_signal(c0, c1, c2, c3)

            if exit_signal == "NONE":
                exit_signal = momentum_signal(c2, c3)

        else:

            h0, h1, h2, h3 = df['High'].iloc[-4], df['High'].iloc[-3], df['High'].iloc[-2], df['High'].iloc[-1]
            l0, l1, l2, l3 = df['Low'].iloc[-4], df['Low'].iloc[-3], df['Low'].iloc[-2], df['Low'].iloc[-1]

            if l2 < l1 and l2 < l3 and h3 > h2:
                exit_signal = "BUY"

            elif h2 > h1 and h2 > h3 and l3 < l2:
                exit_signal = "SELL"

            elif h0 < h1 < h2 < h3 and l0 < l1 < l2 < l3:
                exit_signal = "BULL"

            elif h0 > h1 > h2 > h3 and l0 > l1 > l2 > l3:
                exit_signal = "BEAR"

            else:

                c0, c1, c2, c3 = (
                    df['Close'].iloc[-4],
                    df['Close'].iloc[-3],
                    df['Close'].iloc[-2],
                    df['Close'].iloc[-1]
                )

                exit_signal = three_candle_signal(c1, c2, c3)

                if exit_signal == "NONE":
                    exit_signal = four_candle_signal(c0, c1, c2, c3)

                if exit_signal == "NONE":
                    exit_signal = momentum_signal(c2, c3)

        # ==============================
        # ALIGNMENT RULE
        # ==============================
        if entry_signal == "BULL" and exit_signal == "BUY":
            entry_signal = "BUY"

        elif entry_signal == "BEAR" and exit_signal == "SELL":
            entry_signal = "SELL"

        return entry_signal, exit_signal

    except Exception as e:
        print("[ERROR]", e)
        return "BEAR", "BEAR"


# ==================================================
# RUN
# ==================================================
if __name__ == "__main__":
    e, x = get_signal()
    print(e, x)
