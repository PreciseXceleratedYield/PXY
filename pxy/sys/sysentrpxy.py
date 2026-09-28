import pandas as pd
from syscnfgpxy import TICKER
from sysmktpxy import get_signal
from sysstrndpxy import calculate_supertrend

def get_entry_signal(df=None, use_st_filter=False):
    """
    Direct copy-and-override signal router matching market execution to OTM strategies.
    
    Parameters:
    - use_st_filter (bool): 
        * False (Default): No-Filter Mode. Every BULL/BEAR directly becomes OTMBUY/OTMSELL.
        * True: Strict Filter Mode. SuperTrend alignment is strictly enforced.
    """
    if df is None:
        from sysdtafpxy import fetch_yf_data
        df = fetch_yf_data()
        
    if df is None or df.empty:
        return "NONE", "NONE"

    # 1️⃣ Fetch base raw market signals
    mkt_entry_dir, _ = get_signal(df)  # Raw market exit signal completely ignored
    mkt_entry_dir = str(mkt_entry_dir).upper().strip()

    # 2️⃣ Fetch SuperTrend regime
    processed_st_df = calculate_supertrend(df.copy())
    if processed_st_df.empty:
        trend = "NONE"
    else:
        trend = str(processed_st_df["ST_Trend"].iloc[-1]).upper().strip()

    # 🎯 ENTRY LAYER (Switch Logic)
    if use_st_filter:
        # Strict Filtering: Check trend alignment
        if mkt_entry_dir == "BULL" and trend == "BULL":
            mapped_entry = "OTMBUY"
        elif mkt_entry_dir == "BEAR" and trend == "BEAR":
            mapped_entry = "OTMSELL"
        else:
            mapped_entry = "NONE"  # Block mismatched trends
    else:
        # No Filter Mode: Direct upgrade pass-through mapping
        if mkt_entry_dir == "BULL":
            mapped_entry = "OTMBUY"
        elif mkt_entry_dir == "BEAR":
            mapped_entry = "OTMSELL"
        else:
            mapped_entry = "NONE"

    # 🎯 EXIT LAYER: Decoupled and clean mapping based strictly on mapped_entry status
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
        print("RUNNING ENTRY PASSTHROUGH SIGNAL ROUTER DECOUPLED MATRIX...")
        # Runs in No-Filter Mode by default
        entry_sig, exit_sig = get_entry_signal(df)
        print(f"ROUTER SIGNALS >> ENTRY_SIG: {entry_sig} | EXIT_SIG: {exit_sig}")

