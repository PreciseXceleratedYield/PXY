import pandas as pd 
from syscnfgpxy import TICKER 
from sysmktpxy import get_signal 

def get_entry_signal(df=None):
    """
    Routes options positioning dynamically using SuperTrend as the primary engine.
    If SuperTrend is 'SIDE', it resolves the direction using the market signal.
    """
    if df is None:
        from sysdtafpxy import fetch_yf_data
        df = fetch_yf_data()
        
    if df is None or df.empty:
        return "NONE", "NONE"

    # Fetch baseline directional flags upfront
    _, mkt_exit_dir = get_signal(df)
    
    # Calculate SuperTrend as the primary matrix
    from sysstrndpxy import calculate_supertrend
    processed_st_df = calculate_supertrend(df.copy())
    if processed_st_df.empty:
        return "NONE", "NONE"
        
    trend = processed_st_df["ST_Trend"].iloc[-1]

    # Global "NONE" Safety Filter
    if trend not in ["BULL", "BEAR", "SIDE"] or mkt_exit_dir not in ["BULL", "BEAR"]:
        return "NONE", "NONE"

    # =====================================================================
    # 🎯 PRIMARY ROUTING ENGINE MATRIX (SuperTrend Core)
    # =====================================================================
    if trend == "BULL":
        if mkt_exit_dir == "BULL": 
            return "OTMBUY", "BULL"
        elif mkt_exit_dir == "BEAR": 
            return "EXITCE", "BULL"
            
    elif trend == "BEAR":
        if mkt_exit_dir == "BEAR": 
            return "OTMSELL", "BEAR"
        elif mkt_exit_dir == "BULL": 
            return "EXITPE", "BEAR"
            
    # =====================================================================
    # ⚡ FALLBACK: Resolve with Market Signal when SuperTrend is SIDE
    # ================================================


