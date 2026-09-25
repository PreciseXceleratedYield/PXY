import pandas as pd
from syscnfgpxy import TICKER
from sysmktpxy import get_signal
from sysstrndpxy import calculate_supertrend

def get_entry_signal(df=None):
    """
    Direct copy-and-override signal router matching market execution to OTM strategies.
    - Entry Signal: Maps to OTMBUY/OTMSELL if market is BULL/BEAR and ST is matching or SIDE.
    - Exit Signal: Copied directly from Entry status:
        * OTMBUY   -> BULL
        * OTMSELL  -> BEAR
        * All other instances -> NONE
    """
    if df is None:
        from sysdtafpxy import fetch_yf_data
        df = fetch_yf_data()
        
    if df is None or df.empty:
        return "NONE", "NONE"

    # 1️⃣ Fetch base raw market signals
    mkt_entry_dir, _ = get_signal(df)  # Raw market exit signal completely ignored
    mkt_entry_dir = str(mkt_entry_dir).upper().strip()

    # 2️⃣ Fetch SuperTrend regime to check entry filtering criteria
    processed_st_df = calculate_supertrend(df.copy())
    if processed_st_df.empty:
        trend = "NONE"
    else:
        trend = str(processed_st_df["ST_Trend"].iloc[-1]).upper().strip()

    # 🎯 ENTRY FILTER LAYER: Convert directional market signals when ST is matching or SIDE
    if mkt_entry_dir == "BULL" and trend in ["BULL"]:
        mapped_entry = "OTMBUY"
    elif mkt_entry_dir == "BEAR" and trend in ["BEAR"]:
        mapped_entry = "OTMSELL"
    else:
        mapped_entry = mkt_entry_dir

    # 🎯 EXIT FILTER LAYER: Mirrored directly from entry logic states
    if mapped_entry == "OTMBUY":
        mapped_exit = "BULL"
    elif mapped_entry == "OTMSELL":
        mapped_exit = "BEAR"
    else:
        mapped_exit = "NONE"

    return mapped_entry, mapped_exit

if __name__ == "__main__":
    from sysdtafpxy import fetch_yf_data
    df = fetch_yf_data()
    if df is not None and not df.empty:
        print("RUNNING RAW ENTRY PASS-THROUGH SIGNAL ROUTER MATRIX...")
        entry_sig, exit_sig = get_entry_signal(df)
        print(f"ROUTER SIGNALS >> ENTRY_SIG: {entry_sig} | EXIT_SIG: {exit_sig}")

