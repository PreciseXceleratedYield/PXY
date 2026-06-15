# sysentrpxy.py
"""
===============================================================================
PXY OPTION ROUTING ENGINE: EXCLUSIVE SYMMETRIC TREND ROUTER (ATM / ATM)
===============================================================================
Operational Rules:
- EXIT raw signals cascade unmutated to the very end.
- ENTRY signals arrive pre-converted from sysmktpxy strictly as BUY or SELL.
- Strike Selection:
  - Trend Aligned     -> ATM BUY / ATM SELL
  - Trend Not Aligned -> ATM BUY / ATM SELL
===============================================================================
"""

from sysmktpxy import get_signal
from sysstrndpxy import calculate_supertrend

def get_entry_signal(df):
    if df is None or df.empty:
        return "NONE", "NONE"

    # 1. READ RAW CASCADED PIPELINE STATES FROM GATEWAY
    # raw_entry is already guaranteed by sysmktpxy to be only "BUY", "SELL", or "NONE"
    raw_entry, exit_sig = get_signal(df)
    exit_sig = str(exit_sig).upper().strip()
    entry_sig = str(raw_entry).upper().strip()

    if entry_sig not in ["BUY", "SELL"]:
        return "NONE", exit_sig

    # 2. EVALUATE SUPERTREND ALIGNMENT
    strnd_df = calculate_supertrend(df)
    strnd_trend = "NEUTRAL"

    if strnd_df is not None and not strnd_df.empty:
        try:
            strnd_trend = str(strnd_df.iloc[-1]['sma_trend_full']).upper().strip()   
        except Exception:
            pass

    # Establish absolute direction flags from the master supertrend line
    is_trend_bull = strnd_trend in ["BUY", "TBUY", "BULL"]
    is_trend_bear = strnd_trend in ["SELL", "TSELL", "BEAR"]

    # 3. EXCLUSIVE SYMMETRIC STRIKE ROUTING PROCESSING
    if entry_sig == "BUY":
        # Trend Aligned -> ATM | Trend Not Aligned -> ATM
        final_signal = "ATMBUY" if is_trend_bull else "ATMBUY"
        
    else:  # entry_sig is strictly "SELL"
        # Trend Aligned -> ATM | Trend Not Aligned -> ATM
        final_signal = "ATMSELL" if is_trend_bear else "ATMSELL"

    return final_signal, exit_sig

if __name__ == "__main__":
    from sysdthapxy import get_pxy_data
    _, _, _, live_df = get_pxy_data(df=None)
    
    if not live_df.empty:
        final_route, cascaded_exit = get_entry_signal(live_df)
        print(f"ROUTE TARGET CONTRACT: {final_route} | UNMUTATED EXIT SIGNAL: {cascaded_exit}")

