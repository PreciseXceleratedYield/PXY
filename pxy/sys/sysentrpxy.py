import pandas as pd
from syscnfgpxy import TICKER
from sysmktpxy import get_signal
from sysstrndpxy import calculate_supertrend

def get_entry_signal(df=None):
    """
    Finalized System Router Matrix:
    - ENTRY: 
      - ST BULL/BEAR: Contrarian (ST BULL + MKT BEAR -> BUY | ST BEAR + MKT BULL -> SELL)
      - ST SIDE: Pure MKT Copy (MKT BULL -> BUY | MKT BEAR -> SELL)
    - EXIT: 
      - ST BULL/BEAR: Pure ST Copy (BULL -> BULL | BEAR -> BEAR)
      - ST SIDE: Pure MKT Copy (MKT BULL -> BULL | MKT BEAR -> BEAR)
    """
    if df is None:
        from sysdtafpxy import fetch_yf_data
        df = fetch_yf_data()
        
    if df is None or df.empty:
        return "NONE", "NONE"

    # 1️⃣ Fetch base raw signals
    mkt_dir, _ = get_signal(df)
    mkt_exit_dir = str(mkt_dir).upper().strip()

    try:
        processed_st_df = calculate_supertrend(df.copy())
        if processed_st_df is None or processed_st_df.empty:
            trend = "NONE"
        else:
            trend = str(processed_st_df["ST_Trend"].iloc[-1]).upper().strip()
    except Exception as e:
        print(f"⚠️ Trend engine failed ({e}); signals forced to NONE.")
        return "NONE", "NONE"

    # 🎯 ENTRY LAYER (Contrarian in trend, Pure MKT copy in SIDE)
    if trend == "BULL" and mkt_exit_dir == "BEAR":
        mapped_entry = "BUY"
    elif trend == "BEAR" and mkt_exit_dir == "BULL":
        mapped_entry = "SELL"
    elif trend == "SIDE":
        if mkt_exit_dir == "BULL":
            mapped_entry = "BUY"
        elif mkt_exit_dir == "BEAR":
            mapped_entry = "SELL"
        else:
            mapped_entry = "NONE"
    else:
        mapped_entry = "NONE"

    # 🔒 LOCKED EXIT LAYER (ST Copy in trend, Pure MKT copy in SIDE)
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
        print("RUNNING MATRIX (ENTRY AND EXIT COPY MKT ON SIDE)...")
        entry_sig, exit_sig = get_entry_signal(df)
        print(f"ROUTER SIGNALS >> ENTRY_SIG: {entry_sig} | EXIT_SIG: {exit_sig}")
