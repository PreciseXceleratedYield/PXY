import pandas as pd 
from syscnfgpxy import TICKER 
from sysmktpxy import get_signal 
from sysstrndpxy import calculate_supertrend 

# 🎛️ GLOBAL CONFIGURATION SWITCHES 
USE_ST_FILTER = True  # False = No-Filter Mode | True = Strict ST Filtering Mode 

def get_entry_signal(df=None):
    """
    Direct copy-and-override signal router matching market execution to OTM strategies.
    Exits are strictly locked to 'NONE' unless SuperTrend enters a 'SIDE' regime.
    """
    if df is None:
        from sysdtafpxy import fetch_yf_data
        df = fetch_yf_data()
        
    if df is None or df.empty:
        return "NONE", "NONE"
        
    # 1️⃣ Fetch base raw market signals (Both Entry and Exit captured now)
    mkt_entry_dir, mkt_exit_dir = get_signal(df) 
    mkt_entry_dir = str(mkt_entry_dir).upper().strip() 
    mkt_exit_dir = str(mkt_exit_dir).upper().strip() 
    
    # 2️⃣ Fetch SuperTrend regime 
    processed_st_df = calculate_supertrend(df.copy()) 
    if processed_st_df.empty: 
        trend = "NONE" 
    else: 
        trend = str(processed_st_df['ST_Trend'].iloc[-1]).upper().strip() 
        
    # 🎯 ENTRY LAYER (Using global switch) 
    if USE_ST_FILTER: 
        # Strict Filtering: Check trend alignment 
        if mkt_entry_dir == "BULL" and trend == "BULL": 
            mapped_entry = "OTMBUY" 
        elif mkt_entry_dir == "BEAR" and trend == "BEAR": 
            mapped_entry = "OTMSELL" 
        else: 
            mapped_entry = "NONE"  # Block mismatched trends 
    else: 
        # No Filter Mode: Direct upgrade pass-through mapping 
        if mkt_entry_dir == "BULL": 
            mapped_entry = "OTMBUY" 
        elif mkt_entry_dir == "BEAR": 
            mapped_entry = "OTMSELL" 
        else: 
            mapped_entry = "NONE" 
            
    # 🎯 EXIT LAYER: Conditional activation exclusive to the "SIDE" trend state
    if trend == "SIDE":
        mapped_exit = mkt_exit_dir  # Passes through the original raw exit signal value
    else:
        mapped_exit = "NONE"        # Hard lockdown for BULL, BEAR, or empty states
        
    return mapped_entry, mapped_exit 

if __name__ == "__main__": 
    from sysdtafpxy import fetch_yf_data 
    df = fetch_yf_data() 
    if df is not None and not df.empty: 
        print(f"RUNNING MATRIX (USE_ST_FILTER = {USE_ST_FILTER})...") 
        entry_sig, exit_sig = get_entry_signal(df) 
        print(f"ROUTER SIGNALS >> ENTRY_SIG: {entry_sig} | EXIT_SIG: {exit_sig}")
