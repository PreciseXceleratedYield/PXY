# =============================================================================== #
# PXY OPTION ROUTING ENGINE - PURE SUPERTREND PROFILE (ST ONLY)
# =============================================================================== #

import pandas as pd
from syscnfgpxy import TICKER
from sysmktpxy import get_signal


def get_entry_signal(df=None):
    """Routes options positioning purely based on the SuperTrend Profile:

    Entries -> Driven strictly by SuperTrend directions ("BULL" / "BEAR").
               If SuperTrend is "SIDE", entry mirrors the baseline market layout.
    Exits   -> Matches entry direction for "BULL" / "BEAR".
               If SuperTrend is "SIDE", exit falls back to the Market Matrix layout.
    """
    if df is None:
        from sysdtafpxy import fetch_yf_data
        df = fetch_yf_data()

    if df is None or df.empty:
        return "NONE", "NONE"

    # ===== PURE SUPERTREND ENGINE ===== #
    from sysstrndpxy import calculate_supertrend
    
    processed_st_df = calculate_supertrend(df.copy())
    if processed_st_df.empty:
        return "NONE", "NONE"

    trend = processed_st_df["ST_Trend"].iloc[-1]

    # Fetch baseline signals upfront
    _, mkt_exit_dir = get_signal(df)

    if trend == "BULL":
        if mkt_exit_dir == "BULL":
            return "ATMBUY", "BULL"
        elif mkt_exit_dir == "BEAR":
            return "BEAR", "BULL"
        else:
            return "NONE", "BULL"
    
    elif trend == "BEAR":
        if mkt_exit_dir == "BEAR":
            return "ATMSELL", "BEAR"
        elif mkt_exit_dir == "BULL":
            return "BULL", "BEAR"
        else:
            return "NONE", "BEAR"
            
    elif trend == "SIDE":
        # SuperTrend is "SIDE": Both Entry and Exit now mirror the baseline market layout rule.
        if mkt_exit_dir not in ["BULL", "BEAR"]:
            mkt_exit_dir = "NONE"
            
        return mkt_exit_dir, mkt_exit_dir
        
    else:
        # Catch-all safety fallback for unexpected data anomalies
        return "NONE", "NONE"


if __name__ == "__main__":
    from sysdtafpxy import fetch_yf_data

    df = fetch_yf_data()
    if df is not None and not df.empty:
        print("RUNNING ENGINE MATRIX PROFILE [PURE ST MODE]")
        entry, ex = get_entry_signal(df)
        print(f"ROUTER SIGNALS >> ENTRY_SIG: {entry} | EXIT_SIG: {ex}")

