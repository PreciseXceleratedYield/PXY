"""
===============================================================================
PXY OPTION ROUTING ENGINE WITH HYBRID PIPELINES (SUPERTREND + MKTPXY)
===============================================================================
Operational Rules Matrix:
1. Entry signals are driven by absolute matrix conditions between SuperTrend and Market Proxy.
2. Structural exit windows are governed strictly by sysmktpxy execution.
===============================================================================
"""
import pandas as pd
from syscnfgpxy import TICKER
from sysmktpxy import get_signal 
from sysstrndpxy import calculate_supertrend

def get_entry_signal(df=None):
    """
    Routes options positioning based on an absolute decoupled hybrid matrix:
    Entries -> Pure SuperTrend trend state combined with specific Market Proxy outcomes.
    Exits   -> Pure sysmktpxy dynamic signals.
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
        
    # Fixed alignment gap: iloc[-1] targets the exact same closed window bar
    trend = processed_st_df['ST_Trend'].iloc[-1]

    # ===== HYBRID MATRIX ROUTING EVALUATION =====
    
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

