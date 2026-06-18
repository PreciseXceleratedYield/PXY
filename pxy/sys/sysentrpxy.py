"""
===============================================================================
PXY OPTION ROUTING ENGINE: EXCLUSIVE SYMMETRIC TREND ROUTER (ATM / ATM)
===============================================================================
Operational Matrix (Strictly Blueprint Table Synced):
- SUPER: BULL -> ENTRY: BULL     | EXIT: BULL
- SUPER: BEAR -> ENTRY: BEAR     | EXIT: BEAR
- SUPER: SELL -> ENTRY: ATMSELL  | EXIT: SELL
- SUPER: BUY  -> ENTRY: ATMBUY   | EXIT: BUY
===============================================================================
"""

from sysdtafpxy import fetch_yf_data  # Natively gets data here
from sysstrndpxy import calculate_supertrend


def get_entry_signal(df=None):
    # If no data frame is supplied into parameters, automatically extract from sysdtafpxy source
    if df is None:
        df = fetch_yf_data()

    if df is None or df.empty:
        return "NONE", "NONE"

    # 1. EVALUATE MATRIX VALUES VIA 1-PERIOD / 1-FACTOR RULES
    # Attempting standard keywords for single-argument dataframes
    try:
        strnd_df = calculate_supertrend(df, length=1, multiplier=1.0)
    except TypeError:
        try:
            strnd_df = calculate_supertrend(df, n=1, multiplier=1.0)
        except TypeError:
            # Fallback if the underlying function hardcodes its internal period/factor parameters
            strnd_df = calculate_supertrend(df)
            
    super_state = "NEUTRAL"

    if strnd_df is not None and not strnd_df.empty:
        try:
            super_state = str(strnd_df.iloc[-1]["Signal"]).upper().strip()
        except Exception:
            pass

    # 2. MATCH CODES ACCORDING TO YOUR Blueprint MATRIX IMAGE
    if super_state == "BULL":
        final_signal, exit_sig = "BULL", "BULL"
    elif super_state == "BEAR":
        final_signal, exit_sig = "BEAR", "BEAR"
    elif super_state == "SELL":
        final_signal, exit_sig = "ATMSELL", "SELL"
    elif super_state == "BUY":
        final_signal, exit_sig = "ATMBUY", "BUY"
    else:
        final_signal, exit_sig = "NONE", "NONE"

    return final_signal, exit_sig


if __name__ == "__main__":
    # Standard independent execution loop block fetching data out of sysdtafpxy
    final_route, cascaded_exit = get_entry_signal(df=None)
    print(f"ENTRY: {final_route} | EXIT: {cascaded_exit}")


