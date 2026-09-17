import pandas as pd
from syscnfgpxy import TICKER
from sysmktpxy import get_signal

def get_entry_signal(df=None, mode="MKT"):
    """Routes options positioning dynamically based on execution mode.
    
    Modes:
    - "MKT" : (Without Filter) Direct execution mapping purely from raw market signal. Default.
    - "ST"  : (With Filter) Pure SuperTrend Profile regime alignment matrix (Your original logic).
    """
    if df is None:
        from sysdtafpxy import fetch_yf_data
        df = fetch_yf_data()
        
    if df is None or df.empty:
        return "NONE", "NONE"

    # Fetch baseline directional flags upfront
    _, mkt_exit_dir = get_signal(df)

    # =====================================================================
    # 🏎️ MODE: MKT (WITHOUT FILTER)
    # =====================================================================
    if mode == "ST":
        # Global failure check for raw market signal
        if mkt_exit_dir not in ["BULL", "BEAR"]:
            return "NONE", "NONE"
            
        # Direct structural mapping without SuperTrend restrictions
        if mkt_exit_dir == "BULL":
            return "OTMBUY", "BULL"
        elif mkt_exit_dir == "BEAR":
            return "OTMSELL", "BEAR"

    # =====================================================================
    # 🛡️ MODE: ST (WITH FILTER - YOUR ORIGINAL CODE AS-IS)
    # =====================================================================
    elif mode == "ST":
        from sysstrndpxy import calculate_supertrend
        processed_st_df = calculate_supertrend(df.copy())
        
        if processed_st_df.empty:
            return "NONE", "NONE"
            
        trend = processed_st_df["ST_Trend"].iloc[-1]

        # Global "NONE" Safety Filter
        if trend not in ["BULL", "BEAR", "SIDE"] or mkt_exit_dir not in ["BULL", "BEAR"]:
            return "NONE", "NONE"

        # ROUTING ENGINE MATRIX (Your exact original logic)
        if trend == "BULL":
            if mkt_exit_dir == "BULL":
                return "OTMBUY", "BULL"
            elif mkt_exit_dir == "BEAR":
                return "EXITCE", "BULL"

        elif trend == "BEAR":
            if mkt_exit_dir == "BEAR":
                return "OTMSELL", "BEAR"
            elif mkt_exit_dir == "BULL":
                return "EXITPE", "BEAR"

        elif trend == "SIDE":
            if mkt_exit_dir == "BULL":
                return "EXITPE", "BULL"
            elif mkt_exit_dir == "BEAR":
                return "EXITCE", "BEAR"

    # Fallback catch-all for structural safety
    return "NONE", "NONE"

if __name__ == "__main__":
    from sysdtafpxy import fetch_yf_data
    df = fetch_yf_data()
    if df is not None and not df.empty:
        print("RUNNING ENGINE MATRIX PROFILE [CURRENT DEFAULT: MKT MODE]")
        # Calling without passing mode explicitly uses "MKT"
        entry_sig, exit_sig = get_entry_signal(df) 
        print(f"ROUTER SIGNALS >> ENTRY_SIG: {entry_sig} | EXIT_SIG: {exit_sig}")

