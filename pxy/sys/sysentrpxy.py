# =============================================================================== #
# PXY OPTION ROUTING ENGINE WITH MARKET PROXY PIPELINE
# =============================================================================== #

import pandas as pd
from syscnfgpxy import TICKER
from sysmktpxy import get_signal


def get_entry_signal(df=None):
    """Routes options positioning based on market proxy signals:

    Entries -> Driven strictly by raw Market Proxy direction across all windows.
    Exits   -> Driven strictly by raw exit_dir, matching the entry directional logic.
    """
    if df is None:
        from sysdtafpxy import fetch_yf_data
        df = fetch_yf_data()

    if df is None or df.empty:
        return "NONE", "NONE"

    # Extract dynamic structural exit matrix from market proxy
    _, exit_dir = get_signal(df)

    # ===== GLOBAL ENTRY ROUTING EVALUATION ===== #
    if exit_dir == "BULL":
        entry_signal = "OTMBUY"
    elif exit_dir == "BEAR":
        entry_signal = "OTMSELL"
    else:
        entry_signal = "NONE"

    # ===== GLOBAL EXIT SIGNAL MATRIX ===== #
    if exit_dir in ["BULL", "BEAR"]:
        exit_signal = exit_dir
    else:
        exit_signal = "NONE"

    return entry_signal, exit_signal


if __name__ == "__main__":
    from sysdtafpxy import fetch_yf_data

    df = fetch_yf_data()
    if df is not None and not df.empty:
        entry, ex = get_entry_signal(df)
        print(f"ROUTER SIGNALS >> ENTRY_SIG: {entry} | EXIT_SIG: {ex}")


