import pandas as pd
from syscnfgpxy import TICKER
from sysmktpxy import get_signal
from sysstrndpxy import calculate_supertrend

def get_entry_signal(df=None):
    """
    Decoupled signal router:
    - ENTRY LAYER: Dynamic contrarian rules combining ST and MKT proxy.
    - EXIT LAYER: Locked independent rules (ST BULL -> BULL, ST BEAR -> BEAR, ST SIDE -> NONE).
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

    # 🎯 ENTRY LAYER (Contrarian filters)
    if trend in ["BULL", "SIDE"] and mkt_exit_dir == "BEAR":
        mapped_entry = "OTMBUY"
    elif trend in ["BEAR", "SIDE"] and mkt_exit_dir == "BULL":
        mapped_entry = "OTMSELL"
    else:
        mapped_entry = "NONE"

    # 🔒 LOCKED EXIT LAYER (Independent of entry rules)
    if trend == "BULL":
        mapped_exit = "BULL"
    elif trend == "BEAR":
        mapped_exit = "BEAR"
    elif trend == "SIDE":
        mapped_exit = "NONE"       # Forced to NONE during sideways trends
    else:
        mapped_exit = "NONE"

    return mapped_entry, mapped_exit


if __name__ == "__main__":
    from sysdtafpxy import fetch_yf_data
    df = fetch_yf_data()
    if df is not None and not df.empty:
        print("RUNNING MATRIX (EXIT ON SIDE = NONE)...")
        entry_sig, exit_sig = get_entry_signal(df)
        print(f"ROUTER SIGNALS >> ENTRY_SIG: {entry_sig} | EXIT_SIG: {exit_sig}")



