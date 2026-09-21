import pandas as pd 
from syscnfgpxy import TICKER 
from sysmktpxy import get_signal 

def get_entry_signal(df=None):
    """
    Routes options positioning cleanly and directly from the raw market signal.
    """
    if df is None:
        from sysdtafpxy import fetch_yf_data
        df = fetch_yf_data()
        
    if df is None or df.empty:
        return "NONE", "NONE"

    # Fetch baseline directional flags upfront
    _, mkt_exit_dir = get_signal(df)

    # Global failure check for raw market signal
    if mkt_exit_dir not in ["BULL", "BEAR"]:
        return "NONE", "NONE"

    # =====================================================================
    # 🏎️ DIRECT MARKET SIGNAL ROUTING
    # =====================================================================
    if mkt_exit_dir == "BULL":
        return "OTMBUY", "BULL"
        
    elif mkt_exit_dir == "BEAR":
        return "OTMSELL", "BEAR"

    # Fallback catch-all for structural safety
    return "NONE", "NONE"


if __name__ == "__main__":
    from sysdtafpxy import fetch_yf_data
    df = fetch_yf_data()
    if df is not None and not df.empty:
        print("RUNNING ENGINE MATRIX PROFILE [PURE MARKET SIGNAL]")
        entry_sig, exit_sig = get_entry_signal(df)
        print(f"ROUTER SIGNALS >> ENTRY_SIG: {entry_sig} | EXIT_SIG: {exit_sig}")



