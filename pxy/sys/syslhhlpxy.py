# ==================================================
# syslhhlpxy.py  (FINAL FIXED - 45 MIN STATE WINDOW)
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


# ==================================================
# NORMALIZE DATA
# ==================================================
def normalize_df(df):
    if df is None or df.empty:
        return df

    df.columns = [c.lower() for c in df.columns]

    required = {"open", "high", "low", "close"}
    if not required.issubset(df.columns):
        return None

    return df


# ==================================================
# ADAPTER FOR RAW ENGINE
# ==================================================
def to_raw_df(df):
    return df.rename(columns={
        "open": "Open",
        "high": "High",
        "low": "Low",
        "close": "Close"
    })


# ==================================================
# ORB BREAKOUT
# ==================================================
def check_breakout(df, lookback=5):
    if df is None or len(df) < lookback + 1:
        return False

    recent = df.iloc[-(lookback + 1):-1]

    high = recent["high"].max()
    low = recent["low"].min()
    close = df["close"].iloc[-1]

    return close > high or close < low


# ==================================================
# SWING DETECTION
# ==================================================
def detect_swings(df):
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

    return swing_highs, swing_lows


# ==================================================
# BOOTSTRAP BOS (45 MIN FIX)
# ==================================================
def bootstrap_bos(df):
    df = df.tail(45)

    swing_highs, swing_lows = detect_swings(df)

    if not swing_highs and not swing_lows:
        return "UP" if df["close"].iloc[-1] > df["close"].iloc[0] else "DOWN"

    if len(swing_highs) > len(swing_lows):
        return "UP"

    if len(swing_lows) > len(swing_highs):
        return "DOWN"

    return "UP" if df["close"].iloc[-1] > df["close"].iloc[0] else "DOWN"


# ==================================================
# BOS STRUCTURE CHECK
# ==================================================
def check_bos_structure(df, bos_direction, buffer=0):

    close = df["close"].iloc[-1]

    swing_highs, swing_lows = detect_swings(df)

    if not swing_highs or not swing_lows:
        return bos_direction

    last_high = swing_highs[-1]
    last_low = swing_lows[-1]

    if bos_direction == "UP":
        if close < last_low - buffer:
            return "DOWN"

    elif bos_direction == "DOWN":
        if close > last_high + buffer:
            return "UP"

    return bos_direction


# ==================================================
# INITIAL FALLBACK (45 MIN FIX)
# ==================================================
def find_initial_direction(df):
    df = df.tail(45)
    df_raw = to_raw_df(df)
    _, d = detect_raw_direction(df_raw)
    return d if d != "NONE" else "UP"


# ==================================================
# MAIN ENGINE
# ==================================================
def get_phase_direction(df):

    global prev_direction, bos_direction
    global in_bos_phase, transition_active

    df = normalize_df(df)

    if df is None or df.empty:
        return "BOS", "UP"

    df_raw = to_raw_df(df)
    _, raw_dir = detect_raw_direction(df_raw)

    if raw_dir == "NONE":
        raw_dir = prev_direction if prev_direction != "NONE" else "UP"

    # ORB PHASE
    if not in_bos_phase:

        breakout = check_breakout(df)

        if breakout:
            combo = prev_direction + raw_dir

            bos_direction = raw_dir
            in_bos_phase = True
            prev_direction = raw_dir
            transition_active = False

            return "BOS", combo

        prev_direction = raw_dir
        return "ORB", raw_dir

    # BOOTSTRAP
    if bos_direction == "NONE":
        bos_direction = bootstrap_bos(df)
        prev_direction = bos_direction
        transition_active = False

    # BOS STRUCTURE
    new_dir = check_bos_structure(df, bos_direction)

    # ==================================================
    # SAFE TRANSITION (UPDATED OUTPUT FORMAT)
    # ==================================================
    if bos_direction in ("UP", "DOWN") and new_dir != bos_direction and not transition_active:

        if bos_direction == "UP" and new_dir == "DOWN":
            combo = "TRANSDOWN"
        elif bos_direction == "DOWN" and new_dir == "UP":
            combo = "TRASUP"
        else:
            combo = bos_direction + new_dir

        bos_direction = new_dir
        prev_direction = new_dir
        transition_active = True

        return "BOS", combo

    transition_active = False

    return "BOS", bos_direction


# ==================================================
# RUN
# ==================================================
if __name__ == "__main__":

    df = fetch_yf_data()

    phase, direction = get_phase_direction(df)

    print(f"{phase} | {direction}")
