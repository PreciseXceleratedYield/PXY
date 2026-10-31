# Change this line in execepepxy.py
def get_target_quantities(supertrend, ce_lots, pe_lots, lot_size=None):
    """
    Calculates target lot limits from the strict one-lot safety ceiling.
    """
    MODE = "STRICT_NN" #"TREND" 
    HARD_MAX_LIMIT_LOTS = 1

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
