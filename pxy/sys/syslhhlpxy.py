# ==================================================
# syslhhlpxy.py  (FINAL - PHASE + DIRECTION)
# ==================================================

from sysexitpxy import detect_raw_direction
from sysdtafpxy import fetch_yf_data

# ------------------------
# STATE
# ------------------------
prev_direction = "NONE"
bos_direction = "NONE"

in_bos_phase = False
transition_active = False


# ------------------------
# BREAKOUT (ORB → BOS)
# ------------------------
def check_breakout(df, lookback=5):
    if df is None or len(df) < lookback + 1:
        return False

    recent = df.iloc[-(lookback+1):-1]

    high = recent["high"].max()
    low = recent["low"].min()
    close = df["Close"].iloc[-1]

    return close > high or close < low


# ------------------------
# LAST 3 SWINGS
# ------------------------
def detect_last_3_swings(df):
    if df is None or len(df) < 5:
        return [], []

    highs = df["high"].values
    lows = df["low"].values

    swing_highs = []
    swing_lows = []

    for i in range(2, len(df) - 2):

        if highs[i] > highs[i-1] and highs[i] > highs[i-2] and \
           highs[i] > highs[i+1] and highs[i] > highs[i+2]:
            swing_highs.append(highs[i])

        if lows[i] < lows[i-1] and lows[i] < lows[i-2] and \
           lows[i] < lows[i+1] and lows[i] < lows[i+2]:
            swing_lows.append(lows[i])

    return swing_highs[-3:], swing_lows[-3:]


# ------------------------
# BOS STRUCTURE
# ------------------------
def check_bos_structure(df, bos_direction, buffer=0):

    close = df["Close"].iloc[-1]

    swing_highs, swing_lows = detect_last_3_swings(df)

    if not swing_highs or not swing_lows:
        return bos_direction

    last_high = swing_highs[-1]
    last_low = swing_lows[-1]

    if bos_direction == "UP":
        if close < (last_low - buffer):
            return "DOWN"

    elif bos_direction == "DOWN":
        if close > (last_high + buffer):
            return "UP"

    return bos_direction


# ------------------------
# INITIAL FALLBACK
# ------------------------
def find_initial_direction(df):
    if df is None or len(df) < 2:
        return "NONE"

    _, d = detect_raw_direction(df)
    return d if d != "NONE" else "UP"


# ------------------------
# MAIN FUNCTION
# ------------------------
def get_phase_direction(df):
    global prev_direction, bos_direction
    global in_bos_phase, transition_active

    if df is None or df.empty:
        return "ORB", "NONE"

    # ------------------------
    # RAW DIR
    # ------------------------
    _, raw_dir = detect_raw_direction(df)

    if raw_dir == "NONE":
        raw_dir = prev_direction if prev_direction != "NONE" else "UP"

    # ------------------------
    # ORB PHASE
    # ------------------------
    if not in_bos_phase:

        breakout = check_breakout(df)

        if breakout:
            combo = prev_direction + raw_dir

            bos_direction = raw_dir
            in_bos_phase = True

            prev_direction = raw_dir
            transition_active = True

            return "BOS", combo  # transition happens at BOS start

        prev_direction = raw_dir
        return "ORB", raw_dir

    # ------------------------
    # BOS INIT SAFETY
    # ------------------------
    if bos_direction == "NONE":
        bos_direction = find_initial_direction(df)

    # ------------------------
    # BOS STRUCTURE
    # ------------------------
    new_dir = check_bos_structure(df, bos_direction)

    # ------------------------
    # TRANSITION (1 candle)
    # ------------------------
    if new_dir != bos_direction and not transition_active:

        combo = bos_direction + new_dir

        bos_direction = new_dir
        prev_direction = new_dir
        transition_active = True

        return "BOS", combo

    # reset transition
    transition_active = False

    return "BOS", bos_direction


# ==================================================
# SELF RUN
# ==================================================
if __name__ == "__main__":

    df = fetch_yf_data()

    phase, direction = get_phase_direction(df)

    print(f"{phase} | {direction}")
