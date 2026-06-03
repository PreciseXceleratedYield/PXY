# sysstrndpxy.py
import numpy as np
import pandas as pd

# Global Config 
DEBUG_MODE = True 
CHECK_CONFIRMED_ONLY = True  # 🔒 True = Past 2 vs Past 1 (Non-Reprinting) | ⚡ False = Past 1 vs Live Running Now

def get_signal(df: pd.DataFrame) -> tuple:
    """
    Lean Strategic Sorting Engine. 
    Accepts fully pre-calculated Mode 5 upstream DataFrames containing:
    'src_c', 'pxy_st_line', 'pxy_st_no_ll', 'pxy_st_no_hh', and 'bar_count_session'.
    """
    if df is None or len(df) < 5:
        return "NONE", "NONE"

    try:
        n = len(df)
        
        # 1. EXTRACT DATA DIRECTLY FROM UPSTREAM MATRIX COLUMNS
        src_c = df['src_c'].to_numpy()
        pxy_st_line = df['pxy_st_line'].to_numpy()
        pxy_st_no_ll = df['pxy_st_no_ll'].to_numpy()
        pxy_st_no_hh = df['pxy_st_no_hh'].to_numpy()
        
        # Fallback check if your upstream engine labels the session count differently
        bar_count_session = df['bar_count_session'].to_numpy() if 'bar_count_session' in df.columns else np.arange(1, n + 1)

        # 2. RESOLVE DYNAMIC LOOKUP INDEXES TO SYNC WITH PINE OFFSETS
        if CHECK_CONFIRMED_ONLY:
            # 🔒 Confirmed Non-Reprinting: Past 2 (n-3) vs Past 1 (n-2)
            # Perfect sync with Pine Script's [2] vs [1] offsets
            idx_0 = n - 2
            idx_1 = n - 3
        else:
            # ⚡ Live Fast Track: Past 1 (n-2) vs Live Running (n-1)
            # Perfect sync with Pine Script's [1] vs [0] offsets
            idx_0 = n - 1
            idx_1 = n - 2

        # 3. MAP CROSSOVER COORDINATES
        c0 = src_c[idx_0]
        c1 = src_c[idx_1]
        
        st0 = pxy_st_line[idx_0]
        st1 = pxy_st_line[idx_1]
        
        no_ll0 = pxy_st_no_ll[idx_0]
        no_ll1 = pxy_st_no_ll[idx_1]
        
        no_hh0 = pxy_st_no_hh[idx_0]
        no_hh1 = pxy_st_no_hh[idx_1]

        entry, exit_sig = "NONE", "NONE"
        min_bars_required = 3 if CHECK_CONFIRMED_ONLY else 2

        # 4. HIGH-PRIORITY EVALUATION SORTING MATRIX
        if bar_count_session[idx_0] >= min_bars_required:
            cross_buy  = (c0 > st0) and (c1 <= st1)
            cross_sell = (c0 < st0) and (c1 >= st1)
            
            force_buy  = (c0 > no_ll0) and (c1 <= no_ll1)
            force_sell = (c0 < no_hh0) and (c1 >= no_hh1)
            
            # Pure Priority Routing Matrix Execution
            if force_buy:
                entry, exit_sig = "FORCESELL", "FORCESELL"  # Overextension Above Upper Band
            elif force_sell:
                entry, exit_sig = "FORCEBUY", "FORCEBUY"    # Overextension Below Lower Band
            elif cross_buy:
                entry, exit_sig = "CROSSBUY", "CROSSBUY"    # Center Crossover Buy
            elif cross_sell:
                entry, exit_sig = "CROSSSELL", "CROSSSELL"  # Center Crossover Sell

        if DEBUG_MODE:
            print(f"--- PXY STRND PURE STRATEGY MATRIX ---")
            print(f"Active Lookup Window -> Target Index: {idx_0} | Prior Index: {idx_1}")
            print(f"Upstream Close Close -> C0: {c0:.2f} | C1: {c1:.2f}")
            print(f"Upstream Center Line -> ST0: {st0:.2f} | ST1: {st1:.2f}")
            print(f"Calculated Strategy Output -> {entry}\n")

        return entry, exit_sig

    except Exception as e:
        if DEBUG_MODE:
            print(f"PXY Strategy Module Exception Block Met: {e}")
        return "NONE", "NONE"



