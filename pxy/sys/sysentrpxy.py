# =============================================================================== #
# PXY OPTION ROUTING ENGINE WITH HYBRID PIPELINE SWITCH (ST / MKT)
# =============================================================================== #

from datetime import datetime
import pandas as pd
from syscnfgpxy import TICKER
from sysmktpxy import get_signal

# PIPELINE CONFIGURATION SWITCH: Set to "ST" for SuperTrend or "MKT" for Market Proxy
PIPE = "MKT" 


def execute_mkt_pipeline(df):
    """
    Core Market Proxy routing rule. Consolidating this logic guarantees 
    identical behavior across the Morning Filter, MKT Config, and SIDE fallbacks.
    """
    _, exit_dir = get_signal(df)

    if exit_dir == "BULL":
        return "OTMBUY", "BULL"
    elif exit_dir == "BEAR":
        return "OTMSELL", "BEAR"
    else:
        return "NONE", "NONE"


def get_entry_signal(df=None):
    """Routes options positioning based on the configured pipeline switch:

    Entries -> Driven by SuperTrend directions ("ST") or Market Proxy outcomes ("MKT").
    Exits   -> Mirrors the active pipeline's structural direction layout.
    
    Priority Hierarchy:
    1. Morning Filter (09:15 - 09:30 AM) -> HIGHEST PRIORITY. Forces MKT logic instantly.
    2. PIPE Switch ("MKT") -> Bypasses ST, executes MKT logic.
    3. PIPE Switch ("ST") -> Evaluates SuperTrend. If "SIDE", falls back to MKT logic.
    """
    if df is None:
        from sysdtafpxy import fetch_yf_data
        df = fetch_yf_data()

    if df is None or df.empty:
        return "NONE", "NONE"

    # ----- PRIORITY 1: MORNING FILTER CHECK ----- #
    if isinstance(df.index, pd.DatetimeIndex) and len(df) > 0:
        current_time = df.index[-1].time()
    else:
        current_time = datetime.now().time()

    forced_mkt_start = datetime.strptime("09:15", "%H:%M").time()
    forced_mkt_end = datetime.strptime("09:30", "%H:%M").time()
    
    # Absolute top priority bypass
    if forced_mkt_start <= current_time <= forced_mkt_end:
        return execute_mkt_pipeline(df)

    # ===== PIPELINE ROUTING ENGINE ===== #
    
    # PRIORITY 2: Configured directly to Market Proxy Matrix
    if PIPE == "MKT":
        return execute_mkt_pipeline(df)

    # PRIORITY 3: Configured to SuperTrend Supreme Profile
    elif PIPE == "ST":
        from sysstrndpxy import calculate_supertrend
        
        processed_st_df = calculate_supertrend(df.copy())
        if processed_st_df.empty:
            return "NONE", "NONE"

        trend = processed_st_df["ST_Trend"].iloc[-1]

        if trend == "BULL":
            return "OTMBUY", "BULL"
        elif trend == "BEAR":
            return "OTMSELL", "BEAR"
        else:
            # Fallback when SuperTrend is "SIDE" or undefined
            return execute_mkt_pipeline(df)

    return "NONE", "NONE"


if __name__ == "__main__":
    from sysdtafpxy import fetch_yf_data

    df = fetch_yf_data()
    if df is not None and not df.empty:
        print(f"RUNNING ENGINE MATRIX PROFILE [PIPE={PIPE}]")
        entry, ex = get_entry_signal(df)
        print(f"ROUTER SIGNALS >> ENTRY_SIG: {entry} | EXIT_SIG: {ex}")


