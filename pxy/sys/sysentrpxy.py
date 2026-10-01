import pandas as pd
from syscnfgpxy import TICKER
from sysmktpxy import get_signal
from sysstrndpxy import calculate_supertrend

def get_entry_signal(df=None):
    """
    Simplified direct router:
    - SuperTrend strictly dictates the ENTRY (BULL -> OTMBUY, BEAR -> OTMSELL).
    - Market signal strictly dictates the EXIT (BULL -> BULL, BEAR -> BEAR).
    """
    if df is None:
        from sysdtafpxy import fetch_yf_data
        df = fetch_yf_data()
        
    if df is None or df.empty:
        return "NONE", "NONE"

    # 1️⃣ Fetch base raw market exit signals
    mkt_dir, _ = get_signal(df)
    mkt_exit_dir = str(mkt_dir).upper().strip()

    # 2️⃣ Fetch SuperTrend entry signals
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

    # 🎯 EXIT LAYER: Purely driven by Market proxy signal
    if mkt_exit_dir == "BULL":
        mapped_exit = "BULL"
    elif mkt_exit_dir == "BEAR":
        mapped_exit = "BEAR"
    else:
        mapped_exit = "NONE"

    return mapped_entry, mapped_exit


if __name__ == "__main__":
    from sysdtafpxy import fetch_yf_data
    df = fetch_yf_data()
    if df is not None and not df.empty:
        print("RUNNING SIMPLIFIED ST ENTRY / MKT EXIT MATRIX...")
        entry_sig, exit_sig = get_entry_signal(df)
        print(f"ROUTER SIGNALS >> ENTRY_SIG: {entry_sig} | EXIT_SIG: {exit_sig}")

