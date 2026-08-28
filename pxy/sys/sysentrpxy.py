# ===============================================================================
# PXY OPTION ROUTING ENGINE (PURE TSMA SIGNALS ONLY)
# ===============================================================================
import pandas as pd
from sysrtsmapxy import calculate_linear_regression_channel

def get_entry_signal(df=None):
    """
    Routes options positioning based on an absolute decoupled trend matrix:
    Entries & Exits -> Driven 100% by pure TSMA (Linear Regression) states.
    """
    if df is None:
        from sysdtafpxy import fetch_yf_data
        df = fetch_yf_data()
        
    if df is None or df.empty:
        return "NONE", "NONE"

    # 1. Process technical TSMA profiles (9-Period Linear Regression Curve)
    processed_tsma_df = calculate_linear_regression_channel(df.copy())
    
    if processed_tsma_df.empty:
        return "NONE", "NONE"
        
    # Target exact same closed window bar from the linreg dashboard mapping
    tsma_trend = processed_tsma_df['ST_Trend'].iloc[-1]

    # Assign both exit matrix and entries cleanly from the TSMA trend state
    exit_dir = tsma_trend

    # ===== PURE TSMA MATRIX ROUTING EVALUATION =====
    if tsma_trend == "BULL":
        entry_signal = "OTMBUY"
    elif tsma_trend == "BEAR":
        entry_signal = "OTMSELL"
    else:
        entry_signal = "NONE"

    return entry_signal, exit_dir

if __name__ == "__main__":
    # Test execution block
    entry, exit_sig = get_entry_signal()
    print(f"\n[TSMA Engine] -> Entry: {entry} | Exit Matrix: {exit_sig}")



