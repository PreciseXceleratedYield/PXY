import pandas as pd
from syscnfgpxy import TICKER
from sysmktpxy import get_signal
from sysstrndpxy import calculate_supertrend

def get_entry_signal(df=None):
    """
    Direct copy-and-override signal router.
    - Entry Signal: Maps BULL/BEAR to OTM between 9:00 AM - 9:30 AM IST, and ATM after 9:30 AM IST.
    - Exit Signal: Copies raw market exit signal, overridden to SIDE only when ST is SIDE.
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

    # ⏰ Check time condition (IST) based on the latest available row
    latest_time = df.index[-1].time()
    start_otm = pd.to_datetime("09:00").time()
    end_otm = pd.to_datetime("09:30").time()

    # Determine execution type based on the time window
    if start_otm <= latest_time <= end_otm:
        suffix = "OTM"
    else:
        suffix = "ATM"

    # 🎯 CONVERT ENTRY: Map raw direction strings using the time-based prefix
    if mkt_entry_dir == "BULL":
        mapped_entry = f"{suffix}BUY"
    elif mkt_entry_dir == "BEAR":
        mapped_entry = f"{suffix}SELL"
    else:
        mapped_entry = mkt_entry_dir

    # 2️⃣ Fetch SuperTrend regime to check ONLY for a sideways environment
    processed_st_df = calculate_supertrend(df.copy())
    if processed_st_df.empty:
        return mapped_entry, mkt_exit_dir

    trend = str(processed_st_df["ST_Trend"].iloc[-1]).upper().strip()

    # 🛑 THE ONLY ST INFLUENCE: Override exit channel to SIDE if trend is flat
    if trend == "SIDE":
        return mapped_entry, "SIDE"

    # 🎯 STANDARD PATH: Return mapped entry and raw market exit signal unchanged
    return mapped_entry, mkt_exit_dir

if __name__ == "__main__":
    from sysdtafpxy import fetch_yf_data
    df = fetch_yf_data()
    if df is not None and not df.empty:
        print("RUNNING RAW ENTRY PASS-THROUGH SIGNAL ROUTER MATRIX...")
        entry_sig, exit_sig = get_entry_signal(df)
        print(f"ROUTER SIGNALS >> ENTRY_SIG: {entry_sig} | EXIT_SIG: {exit_sig}")
