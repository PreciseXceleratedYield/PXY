# =============================================================================== #
# PXY OPTION ROUTING ENGINE WITH HYBRID PIPELINE SWITCH (ST / MKT)
# =============================================================================== #

import pandas as pd
from syscnfgpxy import TICKER
from sysmktpxy import get_signal

# PIPELINE CONFIGURATION SWITCH: Set to "ST" for SuperTrend or "MKT" for Market Proxy
PIPE = "MKT" 


def get_entry_signal(df=None):
    """Routes options positioning based on the configured pipeline switch:

    Entries -> Driven by SuperTrend directions ("ST") or Market Proxy outcomes ("MKT").
    Exits   -> Mirrors the active pipeline's structural direction layout.
    """
    if df is None:
        from sysdtafpxy import fetch_yf_data
        df = fetch_yf_data()

    if df is None or df.empty:
        return "NONE", "NONE"

    # ===== PIPELINE ROUTING ENGINE ===== #

    if PIPE == "ST":
        from sysstrndpxy import calculate_supertrend
        
        # 1. Process technical SuperTrend profiles
        processed_st_df = calculate_supertrend(df.copy())
        if processed_st_df.empty:
            return "NONE", "NONE"

        # Target the exact closed window bar trend profile ("BULL" or "BEAR")
        trend = processed_st_df["ST_Trend"].iloc[-1]

        # Route entries and exits via SuperTrend values
        if trend == "BULL":
            entry_signal = "OTMBUY"
            exit_signal = "BULL"
        elif trend == "BEAR":
            entry_signal = "OTMSELL"
            exit_signal = "BEAR"
        else:
            entry_signal = "NONE"
            exit_signal = "NONE"

    else:  # Default to "MKT" Pipeline Matrix
        # 1. Extract dynamic structural matrix from market proxy
        _, exit_dir = get_signal(df)

        # Route entries and exits via Market Proxy direction
        if exit_dir == "BULL":
            entry_signal = "OTMBUY"
            exit_signal = "BULL"
        elif exit_dir == "BEAR":
            entry_signal = "OTMSELL"
            exit_signal = "BEAR"
        else:
            entry_signal = "NONE"
            exit_signal = "NONE"

    return entry_signal, exit_signal


if __name__ == "__main__":
    from sysdtafpxy import fetch_yf_data

    df = fetch_yf_data()
    if df is not None and not df.empty:
        print(f"RUNNING ENGINE MATRIX PROFILE [PIPE={PIPE}]")
        entry, ex = get_entry_signal(df)
        print(f"ROUTER SIGNALS >> ENTRY_SIG: {entry} | EXIT_SIG: {ex}")



