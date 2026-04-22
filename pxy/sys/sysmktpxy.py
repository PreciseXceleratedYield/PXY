# ==================================================
# PRO SIGNAL ENGINE (HA STATE-ALIGNED - NO NONE VERSION)
# ==================================================

from sysdtafpxy import fetch_yf_data

# ==================================================
# SWITCHES
# ==================================================
MODE = "HKIN"
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
# CANDLE STATE (CORE IDEA)
# ==================================================
def candle_state(o, c):
    if c > o:
        return 1      # GREEN
    elif c < o:
        return -1     # RED
    return 0          # DOJI


# ==================================================
# HKIN STATE ENGINE (NO NONE LOGIC)
# ==================================================
def hkin_state_signal(prev_o, prev_c, curr_o, curr_c):

    prev_state = candle_state(prev_o, prev_c)
    curr_state = candle_state(curr_o, curr_c)

    dbg("STATE:", prev_state, curr_state)

    # 🔥 transition logic (main driver)
    if curr_state > prev_state:
        return "BUY"

    if curr_state < prev_state:
        return "SELL"

    # 🔥 continuation logic
    if curr_state == 1:
        return "BULL"

    if curr_state == -1:
        return "BEAR"

    # 🔥 fallback (NEVER NONE)
    return "BULL" if prev_state >= 0 else "BEAR"


# ==================================================
# EXIT STATE ENGINE (STABLE TREND SCORE)
# ==================================================
def exit_state_signal(df):

    closes = df['Close'].iloc[-4:].values

    score = 0

    for i in range(1, len(closes)):
        if closes[i] > closes[i - 1]:
            score += 1
        else:
            score -= 1

    if score >= 2:
        return "BUY"
    elif score <= -2:
        return "SELL"
    elif score == 1:
        return "BULL"
    else:
        return "BEAR"


# ==================================================
# MASTER ENGINE
# ==================================================
def get_signal():

    try:
        df = get_df()

        if df is None:
            return "BEAR", "BEAR"

        # ==============================
        # HKIN MODE (STATE-BASED ENGINE)
        # ==============================
        from sysdthapxy import get_ha_data

        _, _, _, df = get_ha_data(df=df)

        if df is None:
            return "BEAR", "BEAR"

        # 🔥 USE CLOSED CANDLES ONLY (-3, -2)
        prev_o = df["HA_Open"].iloc[-3]
        prev_c = df["HA_Close"].iloc[-3]

        curr_o = df["HA_Open"].iloc[-2]
        curr_c = df["HA_Close"].iloc[-2]

        entry_signal = hkin_state_signal(prev_o, prev_c, curr_o, curr_c)

        # ==============================
        # EXIT ENGINE
        # ==============================
        exit_signal = exit_state_signal(df)

        # ==============================
        # ALIGNMENT RULE (SAFE OVERRIDE)
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
