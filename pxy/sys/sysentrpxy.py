# ==================================================
# sysentrpxy.py (PURE DEPTH FILTER VERSION)
# ==================================================

from sysmktpxy import get_signal
from syshkinpxy import detect_ha_flip_signal


# ==================================================
# CORE ENGINE (MINIMAL)
# ==================================================
def get_entry_signal(df=None):

    # ------------------------------
    # BASE SIGNAL (UNCHANGED)
    # ------------------------------
    signal, exit_signal = get_signal()

    # ------------------------------
    # DEPTH CHECK
    # ------------------------------
    try:
        _, past_depth, _, _ = detect_ha_flip_signal()

        if past_depth == "NA":
            return "NONE", exit_signal

        side = past_depth[:2]   # CE / PE
        depth = int(past_depth[2:])

    except:
        return "NONE", exit_signal

    # ------------------------------
    # ONLY CONDITION (YOUR RULE)
    # ------------------------------
    if signal == "BUY" and side == "PE" and depth > 5:
        return "ATMBUY", exit_signal

    if signal == "SELL" and side == "CE" and depth > 5:
        return "ATMSELL", exit_signal

    # ------------------------------
    # EVERYTHING ELSE BLOCKED
    # ------------------------------
    return "NONE", exit_signal


# ==================================================
# TEST
# ==================================================
if __name__ == "__main__":
    entry, exit_signal = get_entry_signal()
    print("ENTRY:", entry)
    print("EXIT :", exit_signal)
