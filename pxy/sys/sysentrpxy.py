import pandas as pd
from syscnfgpxy import TICKER
from sysmktpxy import get_signal
from sysstrndpxy import calculate_supertrend

def get_entry_signal(df=None):
    """
    Direct router with dynamic filters:
    - ENTRY: Driven strictly by SuperTrend (BULL -> OTMBUY, BEAR -> OTMSELL).
    - EXIT: Only fires when SuperTrend is "SIDE". Follows MKT proxy signals (BULL/BEAR), else NONE.
    """
    if df is None:
        from sysdtafpxy import fetch_yf_data
        df = fetch_yf_data()
        
    if df is None or df.empty:
        return "NONE", "NONE"

    # 1️⃣ Fetch base raw market signals
    mkt_dir, _ = get_signal(df)
    mkt_exit_dir = str(mkt_dir).upper().strip()

    # 2️⃣ Fetch SuperTrend signals
    processed_st_df = calculate_supertrend(df.copy())
    if processed_st_df.empty:
        trend = "NONE"
    else:
        trend = str(processed_st_df["ST_Trend"].iloc[-1]).upper().strip()

    # 🎯 ENTRY LAYER: Purely driven by SuperTrend
    if trend == "BULL":
        mapped_entry = "OTMBUY"
    elif trend == "BEAR":
        mapped_entry = "OTMSELL"
    else:
        mapped_entry = "NONE"

    # 🎯 EXIT LAYER: Only allowed if SuperTrend is SIDE, otherwise NONE
    if trend == "SIDE":
        if mkt_exit_dir == "BULL":
            mapped_exit = "BULL"
        elif mkt_exit_dir == "BEAR":
            mapped_exit = "BEAR"
        else:
            mapped_exit = "NONE"
    else:
        mapped_exit = "NONE"

    return mapped_entry, mapped_exit


if __name__ == "__main__":
    from sysdtafpxy import fetch_yf_data
    df = fetch_yf_data()
    if df is not None and not df.empty:
        print("RUNNING ST ENTRY / MKT EXIT (CONDITIONAL ON ST SIDE) MATRIX...")
        entry_sig, exit_sig = get_entry_signal(df)
        print(f"ROUTER SIGNALS >> ENTRY_SIG: {entry_sig} | EXIT_SIG: {exit_sig}")

