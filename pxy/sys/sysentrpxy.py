# ==================================================
# sysentrpxy.py  (PRODUCTION - FINAL)
# ==================================================

from sysmktpxy import get_signal


# ------------------------------
# ENTRY Mapping
# ------------------------------
def _map_entry_signal(entry_signal: str) -> str:
    if entry_signal == "BUY":
        return "ATMBUY"
    elif entry_signal == "SELL":
        return "ATMSELL"
    elif entry_signal in ("BULL", "BEAR"):
        return entry_signal
    else:
        return "NONE"


# ------------------------------
# MAIN FUNCTION
# ------------------------------
def get_entry_signal():
    try:
        entry_signal, exit_signal = get_signal()

        final_entry = _map_entry_signal(entry_signal)
        final_exit = exit_signal  # unchanged

        return final_entry, final_exit

    except Exception:
        return "NONE", "NONE"


# ------------------------------
# MANUAL RUN
# ------------------------------
if __name__ == "__main__":
    entry, exit = get_entry_signal()
    print(f"ENTRY: {entry} | EXIT: {exit}")
