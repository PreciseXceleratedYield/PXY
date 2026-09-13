# =============================================================================== #
# PXY OPTION ROUTING ENGINE - HYBRID SUPERTREND PROFILE (ST + MARKET MATRIX)
# =============================================================================== #

import pandas as pd
from syscnfgpxy import TICKER
from sysmktpxy import get_signal


def get_entry_signal(df=None):
    """Routes options positioning using a Hybrid SuperTrend Profile:

    Primary (BULL/BEAR) -> Driven strictly by SuperTrend directions.
    Fallback (SIDE)      -> Synchronously hands over to Market Matrix rules.
    Exits                -> Always mirrors the active entry direction.
    """
    if df is None:
        from sysdtafpxy import fetch_yf_data
        df = fetch_yf_data()

    if df is None or df.empty:
        return "NONE", "NONE"

    # ===== HYBRID SUPERTREND ENGINE ===== #
    from sysstrndpxy import calculate_supertrend
    
    processed_st_df = calculate_supertrend(df.copy())
    if processed_st_df.empty:
        return "NONE", "NONE"

    trend = processed_st_df["ST_Trend"].iloc[-1]

    # 1. Direct SuperTrend Execution
    if trend == "BULL":
        return "ATMBUY", "BULL"
    
    elif trend == "BEAR":
        return "ATMSELL", "BEAR"
    
    # 2. Synchronized Side Trend Fallback (Mix Mode)
    elif trend == "SIDE":
        _, mkt_exit_dir = get_signal(df)
        
        if mkt_exit_dir == "BULL":
            return "ATMBUY", "BULL"
        elif mkt_exit_dir == "BEAR":
            return "ATMSELL", "BEAR"
        else:
            return "NONE", "NONE"
        
    else:
        # Catch-all safety fallback for unexpected data anomalies
        return "NONE", "NONE"


if __name__ == "__main__":
    from sysdtafpxy import fetch_yf_data

    df = fetch_yf_data()
    if df is not None and not df.empty:
        print("RUNNING ENGINE MATRIX PROFILE [HYBRID ST/MKT MODE]")
        entry, ex = get_entry_signal(df)
        print(f"ROUTER SIGNALS >> ENTRY_SIG: {entry} | EXIT_SIG: {ex}")

