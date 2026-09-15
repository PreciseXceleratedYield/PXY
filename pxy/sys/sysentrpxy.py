import pandas as pd
from syscnfgpxy import TICKER
from sysmktpxy import get_signal

def get_entry_signal(df=None):
    """Routes options positioning purely based on the SuperTrend Profile.
    
    Pipeline Isolation Architecture:
    - Entry Pipe (entry): Routes structural tokens (OTMBUY, OTMSELL, EXITCE, EXITPE, NONE).
    - Exit Pipe (ex): Routes baseline directional flags (BULL, BEAR, NONE).
    
    Global Failure State Rule:
    - If ANY directional variable resolves to an unstable/missing state ("NONE"),
      BOTH pipelines are immediately terminated to prevent broken execution downstream.
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

    # ===== GLOBAL "NONE" SAFETY FILTER ===== #
    if trend not in ["BULL", "BEAR", "SIDE"] or mkt_exit_dir not in ["BULL", "BEAR"]:
        return "NONE", "NONE"

    # ===== ROUTING ENGINE MATRIX ===== #
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
        # Sideways protection layout: entries convert strictly into non-OTM exit mitigators
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
        print("RUNNING ENGINE MATRIX PROFILE [PURE ST MODE]")
        entry_sig, exit_sig = get_entry_signal(df)
        print(f"ROUTER SIGNALS >> ENTRY_SIG: {entry_sig} | EXIT_SIG: {exit_sig}")


