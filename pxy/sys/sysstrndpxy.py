# sysstrndpxy.py
import numpy as np
import pandas as pd

# Global Config 
DEBUG_MODE = True 
CHECK_CONFIRMED_ONLY = True  # 🔒 True = Past 2 vs Past 1 (Non-Reprinting) | ⚡ False = Past 1 vs Live Running Now

def get_signal(df: pd.DataFrame) -> tuple:
    """
    Lean Strategic Sorting Engine. 
    Accepts fully pre-calculated upstream DataFrames and handles flexible column naming.
    """
    if df is None or len(df) < 5:
        return "NONE", "NONE"

    try:
        n = len(df)
        
        # 1. EXTRACT DATA DIRECTLY WITH STANDALONE KEY FALLBACKS
        # This prevents the key exception error if upstream passes standard names
        src_c = df['src_c'].to_numpy() if 'src_c' in df.columns else df['Close'].to_numpy()
        
        # Maps line indicator names or their default key strings
        pxy_st_line = df['pxy_st_line'].to_numpy() if 'pxy_st_line' in df.columns else (df['ST'].to_numpy() if 'ST' in df.columns else df['Close'].to_numpy())
        pxy_st_no_ll = df['pxy_st_no_ll'].to_numpy() if 'pxy_st_no_ll' in df.columns else pxy_st_line
        pxy_st_no_hh = df['pxy_st_no_hh'].to_numpy() if 'pxy_st_no_hh' in df.columns else pxy_st_line
        
        # Session bar count tracking metric
        bar_count_session = df['bar_count_session'].to_numpy() if 'bar_count_session' in df.columns else np.arange(1, n + 1)

        # 2. RESOLVE DYNAMIC LOOKUP INDEXES TO SYNC WITH PINE OFFSETS
        if CHECK_CONFIRMED_ONLY:
            # 🔒 Confirmed Non-Reprinting: Past 2 (n-3) vs Past 1 (n-2)
            idx_0 = n - 2
            idx_1 = n - 3
        else:
            # ⚡ Live Fast Track: Past 1 (n-2) vs Live Running (n-1)
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

        # 4. HIGH-PRIORITY EVALUATION PATTERN SORTING MATRIX
        if bar_count_session[idx_0] >= min_bars_required:
            cross_buy  = (c0 > st0) and (c1 <= st1)
            cross_sell = (c0 < st0) and (c1 >= st1)
            
            force_buy  = (c0 > no_ll0) and (c1 <= no_ll1)
            force_sell = (c0 < no_hh0) and (c1 >= no_hh1)
            
            # Pure Priority Routing Matrix Execution
            if force_buy:
                entry, exit_sig = "FORCESELL", "FORCESELL"  
            elif force_sell:
                entry, exit_sig = "FORCEBUY", "FORCEBUY"    
            elif cross_buy:
                entry, exit_sig = "CROSSBUY", "CROSSBUY"    
            elif cross_sell:
                entry, exit_sig = "CROSSSELL", "CROSSSELL"  

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


# --- STANDALONE MAIN EXECUTION ENGINE ---
if __name__ == "__main__":
    from sysdthapxy import get_pxy_data
    
    print("\n[PXY STRND ENGINE] Standalone Live Stream Listener Initiated.")
    print(f"Configuration -> CHECK_CONFIRMED_ONLY: {CHECK_CONFIRMED_ONLY}")
    print("--------------------------------------------------")
    
    try:
        print("Polling latest day-specific data from sysdthapxy...")
        # Pull your live pre-calculated data matrix from upstream
        _, _, _, live_df = get_pxy_data(df=None)
        
        if live_df is not None and not live_df.empty:
            print(f"Data Successfully Retrieved. Streaming {len(live_df)} historical matrix intervals.")
            
            # Pass directly into the strategy processing gate
            entry_sig, exit_sig = get_signal(live_df)
            
            print("==================================================")
            print(f"⚡ LIVE STREAM OUTPUT -> Entry: {entry_sig} | Exit: {exit_sig}")
            print("==================================================\n")
        else:
            print("❌ Error: Upstream module returned an empty or invalid DataFrame frame.")
            
    except Exception as e:
        print(f"❌ Critical Connection Exception Hit: {e}")


