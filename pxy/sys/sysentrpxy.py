# =============================================================================== #
# PXY OPTION ROUTING ENGINE - PURE SUPERTREND PROFILE (ST ONLY)
# =============================================================================== #

import pandas as pd
from syscnfgpxy import TICKER
from sysmktpxy import get_signal


def get_entry_signal(df=None):
    """Routes options positioning purely based on the SuperTrend Profile:

    Entries -> Driven strictly by SuperTrend directions ("BULL" / "BEAR").
               If SuperTrend is "SIDE", entry is explicitly forced to "NONE".
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

    if trend == "BULL":
        return "ATMBUY", "BULL"
    
    elif trend == "BEAR":
        return "ATMSELL", "BEAR"
    
    elif trend == "SIDE":
        # SuperTrend is "SIDE": Entry is strictly blocked.
        # Exit pulls the active direction as-is from the baseline market layout rule.
        _, mkt_exit_dir = get_signal(df)
        
        if mkt_exit_dir not in ["BULL", "BEAR"]:
            mkt_exit_dir = "NONE"
            
        return "NONE", mkt_exit_dir
        
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

