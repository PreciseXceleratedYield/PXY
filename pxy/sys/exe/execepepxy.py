import pytz
from datetime import datetime, time

def get_target_quantities_ist(supertrend, ce_lots, pe_lots, lot_size=None):
    """
    Calculates target lot limits by independently tracking live Indian Standard Time (IST).
    """
    MODE = "TREND" 
    
    # 1. Fetch live time independently forced to Indian Standard Time (IST)
    ist_tz = pytz.timezone('Asia/Kolkata')
    current_time_ist = datetime.now(ist_tz).time()
        
    # 2. Independent Guard Limit evaluation based purely on IST
    if time(9, 15) <= current_time_ist <= time(9, 30):
        HARD_MAX_LIMIT_LOTS = 1
    else:
        HARD_MAX_LIMIT_LOTS = 3

    # Route A: Absolute Continuous N:N Balance 
    if MODE == "STRICT_NN":
        max_allowed_ce_lots = pe_lots
        max_allowed_pe_lots = ce_lots

    # Route B: Trend-Driven Asymmetric Matrix
    else:
        if supertrend == "BULL":
            max_allowed_ce_lots = pe_lots + 1  
            max_allowed_pe_lots = ce_lots      
        elif supertrend == "BEAR":
            max_allowed_pe_lots = ce_lots + 1  
            max_allowed_ce_lots = pe_lots      
        else:
            max_allowed_ce_lots = pe_lots      
            max_allowed_pe_lots = ce_lots

    # Apply safety ceilings
    max_allowed_ce_lots = min(max_allowed_ce_lots, HARD_MAX_LIMIT_LOTS)
    max_allowed_pe_lots = min(max_allowed_pe_lots, HARD_MAX_LIMIT_LOTS)

    return max_allowed_ce_lots, max_allowed_pe_lots
