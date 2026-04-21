# ==================================================
# sysentrpxy.py (DEPTH ENTRY + ORIGINAL ENTRY AS EXIT)
# ==================================================

from sysmktpxy import get_signal
from syshkinpxy import detect_ha_flip_signal


# ==================================================
# CORE ENGINE
# ==================================================
def get_entry_signal(df=None):

    # ------------------------------
    # ORIGINAL ENGINE SIGNALS
    # ------------------------------
    entry_signal, exit_signal = get_signal()

    # 🔥 IMPORTANT:
    # We will use ORIGINAL ENTRY as EXIT
    original_entry = entry_signal

    # ------------------------------
    # DEPTH CHECK
    # ------------------------------
    try:
        _, past_depth, _, _ = detect_ha_flip_signal()

        if past_depth == "NA":
            return "NONE", original_entry

        side = past_depth[:2]   # CE / PE
        depth = int(past_depth[2:])

    except:
        return "NONE", original_entry

    # ------------------------------
    # ENTRY FILTER (ONLY YOUR RULE)
    # ------------------------------
    if entry_signal == "BUY" and side == "PE" and depth > 6:
        final_entry = "BUY"

    elif entry_signal == "SELL" and side == "CE" and depth > 6:
        final_entry = "SELL"

    else:
        final_entry = "NONE"

    # ------------------------------
    # 🔁 FINAL RETURN
    # ENTRY = FILTERED
    # EXIT  = ORIGINAL ENTRY
    # ------------------------------
    return final_entry, original_entry


# ==================================================
# TEST
# ==================================================
if __name__ == "__main__":
    entry, exit_signal = get_entry_signal()
    print("ENTRY:", entry)
    print("EXIT :", exit_signal)
