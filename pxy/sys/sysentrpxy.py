import pandas as pd
from syscnfgpxy import TICKER
from sysmktpxy import get_signal
from sysstrndpxy import calculate_supertrend

# 🎛️ GLOBAL CONFIGURATION SWITCHES
USE_ST_FILTER = True  # False = No-Filter Mode (Default) | True = Regime Filtering Mode


def get_entry_signal(df=None):
    """
    Direct copy-and-override signal router matching market execution to OTM strategies.
    Uses the global USE_ST_FILTER switch to control the SuperTrend cascade.
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

    # 🎯 ENTRY LAYER (Using global switch)
    if USE_ST_FILTER:
        # Cascade Logic: If ST is definitive, use ST. If ST is sideways/none, fall back to mktpxy.
        if trend == "BULL" and mkt_entry_dir == "BULL":
            mapped_entry = "OTMBUY"
        elif trend == "BEAR" and mkt_entry_dir == "BEAR":
            mapped_entry = "OTMSELL"
        else:  # trend is "SIDE", "NONE", etc. -> Fall back to mktpxy signal
            if mkt_entry_dir == "BULL":
                mapped_entry = "NONE"
            elif mkt_entry_dir == "BEAR":
                mapped_entry = "NONE"
            else:
                mapped_entry = "NONE"
    else:
        # No Filter Mode: Direct pass-through mapping from mktpxy only
        if mkt_entry_dir == "BULL":
            mapped_entry = "OTMBUY"
        elif mkt_entry_dir == "BEAR":
            mapped_entry = "OTMSELL"
        else:
            mapped_entry = "NONE"

    # 🎯 EXIT LAYER: Decoupled and clean mapping based strictly on mapped_entry status
    # Converts OTM in entry, but maps to clean SIDE directions for exits without OTM prefixes
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
        print(f"RUNNING MATRIX (USE_ST_FILTER = {USE_ST_FILTER})...")
        entry_sig, exit_sig = get_entry_signal(df)
        print(f"ROUTER SIGNALS >> ENTRY_SIG: {entry_sig} | EXIT_SIG: {exit_sig}")



