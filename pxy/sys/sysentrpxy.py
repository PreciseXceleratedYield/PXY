# =============================================================================== #
# PXY OPTION ROUTING ENGINE - PURE SUPERTREND PIPELINE (NO TIME RESTRICTIONS)
# =============================================================================== #

import pandas as pd
from syscnfgpxy import TICKER
from sysstrndpxy import calculate_supertrend


def get_entry_signal(df=None):
    """Routes options positioning strictly based on the technical SuperTrend trend state.

    Entries -> Driven purely by SuperTrend.
    Exits   -> Driven purely by SuperTrend.
    """
    if df is None:
        from sysdtafpxy import fetch_yf_data
        df = fetch_yf_data()

    if df is None or df.empty:
        return "NONE", "NONE"

    # Process technical SuperTrend profiles
    processed_st_df = calculate_supertrend(df.copy())
    if processed_st_df.empty:
        return "NONE", "NONE"

    # Target the exact same closed window bar trend
    trend = processed_st_df["ST_Trend"].iloc[-1]

    # ===== PURE SUPERTREND ENTRY ROUTING ===== #
    if trend in ["BULL", "SIDE"]:
        entry_signal = "OTMBUY"
    elif trend in ["BEAR", "SIDE"]:
        entry_signal = "OTMSELL"
    else:
        entry_signal = "NONE"

    # ===== PURE SUPERTREND EXIT SIGNAL MATRIX ===== #
    if trend in ["BULL", "BEAR"]:
        exit_signal = trend
    else:
        exit_signal = "NONE"

    return entry_signal, exit_signal


if __name__ == "__main__":
    from sysdtafpxy import fetch_yf_data

    df = fetch_yf_data()
    if df is not None and not df.empty:
        entry, ex = get_entry_signal(df)
        print(f"ROUTER SIGNALS >> ENTRY_SIG: {entry} | EXIT_SIG: {ex}")

