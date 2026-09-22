import pandas as pd
from syscnfgpxy import TICKER
from sysmktpxy import get_signal
from sysstrndpxy import calculate_supertrend

def get_entry_signal(df=None):
    """
    Direct copy-and-override signal router.
    - Entry Signal: Completely independent of SuperTrend (pure raw pass-through).
    - Exit Signal: Copies raw market exit signal, overridden to SIDE only when ST is SIDE.
    """
    if df is None:
        from sysdtafpxy import fetch_yf_data
        df = fetch_yf_data()
        
    if df is None or df.empty:
        return "NONE", "NONE"

    # 1️⃣ Fetch base raw market signals (Entry is instantly independent)
    mkt_entry_dir, mkt_exit_dir = get_signal(df)
    mkt_entry_dir = str(mkt_entry_dir).upper().strip()
    mkt_exit_dir = str(mkt_exit_dir).upper().strip()

    # 2️⃣ Fetch SuperTrend regime to check ONLY for a sideways environment
    processed_st_df = calculate_supertrend(df.copy())
    if processed_st_df.empty:
        return mkt_entry_dir, mkt_exit_dir
        
    trend = str(processed_st_df["ST_Trend"].iloc[-1]).upper().strip()

    # 🛑 THE ONLY ST INFLUENCE: Override exit channel to SIDE if trend is flat
    if trend == "SIDE":
        return mkt_entry_dir, "SIDE"

    # 🎯 STANDARD PATH: Return the original raw market signals unchanged
    return mkt_entry_dir, mkt_exit_dir

if __name__ == "__main__":
    from sysdtafpxy import fetch_yf_data
    df = fetch_yf_data()
    if df is not None and not df.empty:
        print("RUNNING RAW ENTRY PASS-THROUGH SIGNAL ROUTER MATRIX...")
        entry_sig, exit_sig = get_entry_signal(df) 
        print(f"ROUTER SIGNALS >> ENTRY_SIG: {entry_sig} | EXIT_SIG: {exit_sig}")

