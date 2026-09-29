import pandas as pd
from syscnfgpxy import TICKER
from sysmktpxy import get_signal

def get_entry_signal(df=None):
    """
    Direct market execution to OTM strategies.
    SuperTrend filters removed: Entries mapped to OTM, Exits pass through as-is.
    """
    if df is None:
        from sysdtafpxy import fetch_yf_data
        df = fetch_yf_data()
        
    if df is None or df.empty:
        return "NONE", "NONE"

    # 1️⃣ Fetch base raw market signals
    mkt_entry_dir, mkt_exit_dir = get_signal(df)
    mkt_entry_dir = str(mkt_entry_dir).upper().strip()
    mkt_exit_dir = str(mkt_exit_dir).upper().strip()

    # 2️⃣ Direct Entry Mapping (No filters applied)
    if mkt_entry_dir == "BULL":
        mapped_entry = "OTMBUY"
    elif mkt_entry_dir == "BEAR":
        mapped_entry = "OTMSELL"
    else:
        mapped_entry = "NONE"

    # 3️⃣ Exit Layer: Passes straight through from the market signal pipe
    mapped_exit = mkt_exit_dir

    return mapped_entry, mapped_exit

if __name__ == "__main__":
    from sysdtafpxy import fetch_yf_data
    df = fetch_yf_data()
    if df is not None and not df.empty:
        print("RUNNING RAW MARKET SIGNAL MATRIX...")
        entry_sig, exit_sig = get_entry_signal(df)
        print(f"ROUTER SIGNALS >> ENTRY_SIG: {entry_sig} | EXIT_SIG: {exit_sig}")

