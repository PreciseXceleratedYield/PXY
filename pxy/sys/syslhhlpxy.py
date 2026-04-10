# ==================================================
# syslhhlpxy.py  (FINAL LHHL ENGINE - FORCE READY)
# ==================================================

from sysexitpxy import detect_raw_direction
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
def to_raw_df(df):
    return df.rename(columns={
        "open": "Open",
        "high": "High",
        "low": "Low",
        "close": "Close"
    })


# ==================================================
def detect_direction(df):
    df_raw = to_raw_df(df)
    _, d = detect_raw_direction(df_raw)
    return d if d in ("UP", "DOWN") else "NONE"


# ==================================================
def get_phase_direction(df):

    df = normalize_df(df)

    if df is None:
        return "BOS", "NONE"

    current_dir = detect_direction(df)

    # ==================================================
    # STATIC MEMORY (local snapshot only per call context)
    # ==================================================
    if not hasattr(get_phase_direction, "prev"):
        get_phase_direction.prev = "NONE"

    prev = get_phase_direction.prev

    # update memory AFTER evaluation
    get_phase_direction.prev = current_dir

    # ==================================================
    # ORB PHASE LOGIC
    # ==================================================
    # FIRST VALID STATE
    if prev == "NONE":
        if current_dir == "UP":
            return "ORB", "ORBUP"
        if current_dir == "DOWN":
            return "ORB", "ORBDOWN"
        return "ORB", "NONE"

    # ==================================================
    # TRANSITION LOGIC (CRITICAL FIX)
    # ==================================================
    if prev == "UP" and current_dir == "DOWN":
        return "ORB", "TRANSDOWN"

    if prev == "DOWN" and current_dir == "UP":
        return "ORB", "TRASUP"

    # ==================================================
    # CONTINUATION LOGIC
    # ==================================================
    if current_dir == "UP":
        return "ORB", "ORBUP"

    if current_dir == "DOWN":
        return "ORB", "ORBDOWN"

    # ==================================================
    # FALLBACK
    # ==================================================
    return "ORB", "NONE"


# ==================================================
if __name__ == "__main__":

    df = fetch_yf_data()

    phase, direction = get_phase_direction(df)

    print(f"{phase} | {direction}")
