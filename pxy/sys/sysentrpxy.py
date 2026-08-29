# =============================================================================== #
# PXY OPTION ROUTING ENGINE WITH HYBRID PIPELINES (SUPERTREND + MKTPXY)
# =============================================================================== #

from datetime import datetime
from zoneinfo import ZoneInfo  # Python 3.9+ standard library for timezones
import pandas as pd
from syscnfgpxy import TICKER
from sysmktpxy import get_signal
from sysstrndpxy import calculate_supertrend


def get_entry_signal(df=None):
    """Routes options positioning based on an absolute decoupled hybrid matrix:

    Entries -> Pure SuperTrend trend state combined with specific Market Proxy
    outcomes. Exits   -> Pure sysmktpxy dynamic signals. Evaluation window matches
    current real-time IST clock.
    """
    if df is None:
        from sysdtafpxy import fetch_yf_data

        df = fetch_yf_data()

    if df is None or df.empty:
        return "NONE", "NONE"

    # 1. Pipeline Segment A: Extract dynamic structural exit matrix from market proxy
    _, exit_dir = get_signal(df)

    # 2. Pipeline Segment B: Process technical SuperTrend profiles
    processed_st_df = calculate_supertrend(df.copy())
    if processed_st_df.empty:
        return "NONE", "NONE"

    # Target the exact same closed window bar trend
    trend = processed_st_df["ST_Trend"].iloc[-1]

    # CONSTANTS - Pure Naive Time Objects for Evaluation
    start_time = pd.Timestamp("09:00:00").time()
    end_time = pd.Timestamp("09:30:00").time()

    # REAL-TIME SYSTEM FIX: Fetch exact current live time in IST
    ist_tz = ZoneInfo("Asia/Kolkata")
    latest_time = datetime.now(ist_tz).time()

    # ===== HYBRID MATRIX ROUTING EVALUATION ===== #
    # 9:00 AM to 10:00 AM IST Window: Filter entry signal strictly by exit_dir
    if start_time <= latest_time < end_time:
        if exit_dir == "BULL":
            entry_signal = "OTMBUY"
        elif exit_dir == "BEAR":
            entry_signal = "OTMSELL"
        else:
            entry_signal = "NONE"

    # Post-10:00 AM IST: Normal Matrix Execution
    else:
        if trend == "BULL":
            if exit_dir == "BULL":
                entry_signal = "OTMBUY"
            elif exit_dir == "BEAR":
                entry_signal = "BEAR"
            else:
                entry_signal = "NONE"
        elif trend == "BEAR":
            if exit_dir == "BEAR":
                entry_signal = "OTMSELL"
            elif exit_dir == "BULL":
                entry_signal = "BULL"
            else:
                entry_signal = "NONE"
        else:
            entry_signal = "NONE"

    # Evaluate Exit Profile via Market Proxy Direction
    if exit_dir in ["BULL", "BEAR"]:
        exit_signal = exit_dir
    else:
        exit_signal = "NONE"

    return entry_signal, exit_signal


if __name__ == "__main__":
    from sysdtafpxy import fetch_yf_data

    df = fetch_yf_data()
    if df is not None and not df.empty:
        entry, ex = get_entry_signal(df)
        print(f"ROUTER SIGNALS >> ENTRY_SIG: {entry} | EXIT_SIG: {ex}")
