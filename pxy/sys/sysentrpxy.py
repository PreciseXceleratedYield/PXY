# ==================================================
# sysentrpxy.py
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
def get_entry_signal(df=None):
    try:
        entry_signal, exit_signal = get_signal(df)

        final_entry = _map_entry_signal(entry_signal)
        final_exit = exit_signal

        return final_entry, final_exit

    except Exception:
        return "NONE", "NONE"
