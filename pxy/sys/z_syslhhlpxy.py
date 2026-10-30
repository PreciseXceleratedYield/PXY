# ==================================================
# syslhhlpxy.py (FINAL - STABLE + FORCE READY)
# ==================================================

from sysdtafpxy import fetch_yf_data


def normalize_df(df):
    if df is None or df.empty:
        return None

    df.columns = [c.lower() for c in df.columns]
    required = {"open", "high", "low", "close"}

    if not required.issubset(df.columns):
        return None

    return df


def detect_direction(df):
    """
    PURE momentum-based direction (stable, no NONE leakage)
    """
    if len(df) < 2:
        return "NONE"

    if df["close"].iloc[-1] > df["close"].iloc[-2]:
        return "UP"
    elif df["close"].iloc[-1] < df["close"].iloc[-2]:
        return "DOWN"
    return "NONE"


def get_phase_direction(df=None):

    if df is None:
        df = fetch_yf_data()

    df = normalize_df(df)

    if df is None:
        return "ORB", "NONE"

    current = detect_direction(df)

    if not hasattr(get_phase_direction, "prev"):
        get_phase_direction.prev = "NONE"

    prev = get_phase_direction.prev
    get_phase_direction.prev = current

    # -----------------------------
    # TRANSITIONS (CRITICAL)
    # -----------------------------
    if prev == "UP" and current == "DOWN":
        return "ORB", "TRANSDOWN"

    if prev == "DOWN" and current == "UP":
        return "ORB", "TRASUP"

    # -----------------------------
    # CONTINUATION
    # -----------------------------
    if current == "UP":
        return "ORB", "ORBUP"

    if current == "DOWN":
        return "ORB", "ORBDOWN"

    # -----------------------------
    # FALLBACK
    # -----------------------------
    if prev == "UP":
        return "ORB", "NONEUP"

    if prev == "DOWN":
        return "ORB", "NONEDOWN"

    return "ORB", "NONE"

# ================= MAIN DEBUG =================
if __name__ == "__main__":
    df = fetch_yf_data()

    phase, state = get_phase_direction(df)

    print("\n" + "=" * 50)
    print("PHASE DEBUG OUTPUT")
    print("=" * 50)
    print("Phase :", phase)
    print("State :", state)
