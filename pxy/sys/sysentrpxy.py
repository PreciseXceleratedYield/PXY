# sysentrpxy.py
"""
===============================================================================
PXY OPTION ROUTING ENGINE: COMPACT EXCLUSIVE MASTER PRODUCTION MATRIX
===============================================================================
"""

from sysmktpxy import get_signal
from sysstrndpxy import calculate_supertrend

def get_entry_signal(df):
    if df is None or df.empty:
        return "NONE", "NONE"

    # 1. READ RAW CASCADED PIPELINE STATES FROM GATEWAY
    # raw_entry is guaranteed by sysmktpxy to only be "BUY", "SELL", or "NONE"
    raw_entry, exit_sig = get_signal(df)
    exit_sig = str(exit_sig).upper().strip()
    entry_sig = str(raw_entry).upper().strip()

    if entry_sig not in ["BUY", "SELL"]:
        return "NONE", exit_sig

    # 2. EVALUATE SUPERTREND ALIGNMENT (ATM ONLY)
    strnd_df = calculate_supertrend(df)
    strnd_trend = "NEUTRAL"

    if strnd_df is not None and not strnd_df.empty:
        try:
            strnd_trend = str(strnd_df.iloc[-1]['sma_trend_full']).upper().strip()   
        except Exception:
            pass

    # Exclusive Alignment Strike Routing Logic Processing
    if entry_sig == "BUY" and strnd_trend in ["BUY", "TBUY", "BULL"]:
        final_signal = "ATMBUY"
    elif entry_sig == "SELL" and strnd_trend in ["SELL", "TSELL", "BEAR"]:
        final_signal = "ATMSELL"
    else:
        final_signal = "NONE"

    return final_signal, exit_sig
