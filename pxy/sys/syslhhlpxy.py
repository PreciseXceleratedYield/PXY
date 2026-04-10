# ==================================================
# syslhhlpxy.py (FINAL FIX - REAL STRUCTURE ENGINE)
# ==================================================

from sysdtafpxy import fetch_yf_data


# ==================================================
def normalize_df(df):
    if df is None or df.empty:
        return None

    df.columns = [c.lower() for c in df.columns]
    required = {"open", "high", "low", "close"}

    if not required.issubset(df.columns):
        return None

    return df


# ==================================================
def detect_price_direction(df):
    """
    PURE PRICE MOMENTUM (NO EXTERNAL DEPENDENCY)
    """
    last = df["close"].iloc[-1]
    prev = df["close"].iloc[-2]

    if last > prev:
        return "UP"
    elif last < prev:
        return "DOWN"
    return "NONE"


# ==================================================
def get_phase_direction(df):

    df = normalize_df(df)

    if df is None or len(df) < 3:
        return "BOS", "NONE"

    # ==================================================
    # CORE SIGNALS
    # ==================================================
    current = detect_price_direction(df)

    # memory (stateless-safe per runtime call)
    if not hasattr(get_phase_direction, "prev"):
        get_phase_direction.prev = "NONE"

    prev = get_phase_direction.prev
    get_phase_direction.prev = current

    # ==================================================
    # ORB BASE LOGIC
    # ==================================================
    if prev == "NONE":

        if current == "UP":
            return "ORB", "ORBUP"

        if current == "DOWN":
            return "ORB", "ORBDOWN"

        return "ORB", "NONE"

    # ==================================================
    # TRANSITION LOGIC (CRITICAL FIX)
    # ==================================================
    if prev == "UP" and current == "DOWN":
        return "ORB", "TRANSDOWN"

    if prev == "DOWN" and current == "UP":
        return "ORB", "TRASUP"

    # ==================================================
    # CONTINUATION LOGIC
    # ==================================================
    if current == "UP":
        return "ORB", "ORBUP"

    if current == "DOWN":
        return "ORB", "ORBDOWN"

    # ==================================================
    # FALLBACK (MINIMIZED NONE)
    # ==================================================
    if prev == "UP":
        return "ORB", "NONEUP"

    if prev == "DOWN":
        return "ORB", "NONEDOWN"

    return "ORB", "NONE"


# ==================================================
if __name__ == "__main__":

    df = fetch_yf_data()

    phase, direction = get_phase_direction(df)

    print(f"{phase} | {direction}")
