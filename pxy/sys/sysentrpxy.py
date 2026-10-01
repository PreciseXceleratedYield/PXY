import pandas as pd
from syscnfgpxy import TICKER
from sysmktpxy import get_signal
from sysstrndpxy import calculate_supertrend

def get_entry_signal(df=None):
    """
    Decoupled signal router:
    - ENTRY LAYER: Dynamic contrarian rules combining ST and MKT proxy.
    - EXIT LAYER: Completely independent and locked.
    """
    if df is None:
        from sysdtafpxy import fetch_yf_data
        df = fetch_yf_data()
        
    if df is None or df.empty:
        return "NONE", "NONE"

    # 1️⃣ Fetch base raw signals
    mkt_dir, _ = get_signal(df)
    mkt_exit_dir = str(mkt_dir).upper().strip()

    processed_st_df = calculate_supertrend(df.copy())
    if processed_st_df.empty:
        trend = "NONE"
    else:
        trend = str(processed_st_df["ST_Trend"].iloc[-1]).upper().strip()

    # 🎯 NEW ENTRY LAYER (Contrarian filters)
    if trend in ["BULL", "SIDE"] and mkt_exit_dir == "BEAR":
        mapped_entry = "OTMBUY"
    elif trend in ["BEAR", "SIDE"] and mkt_exit_dir == "BULL":
        mapped_entry = "OTMSELL"
    else:
        mapped_entry = "NONE"

    # 🔒 LOCKED EXIT LAYER (Completely independent of entry rules)
    if trend == "BULL":
        mapped_exit = "BULL"
    elif trend == "BEAR":
        mapped_exit = "BEAR"
    elif trend == "SIDE":
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
        print("RUNNING NEW ENTRY MATRIX (EXIT LOCKED)...")
        entry_sig, exit_sig = get_entry_signal(df)
        print(f"ROUTER SIGNALS >> ENTRY_SIG: {entry_sig} | EXIT_SIG: {exit_sig}")


