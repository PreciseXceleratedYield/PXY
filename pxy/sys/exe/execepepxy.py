def get_target_quantities(supertrend, ce_lots, pe_lots, lot_size=None):
    """
    Calculates dynamic target lot limits based on opposite-side counts.
    """
    # ---------------------------------------------------------------------
    # ⚙️ LOCAL CONFIGURATION SWITCH
    # "TREND"     -> Maintains N+1 on favored side based on opposite side count.
    # "STRICT_NN" -> Enforces an absolute, continuous N:N balance across all trends.
    # ---------------------------------------------------------------------
    MODE = "STRICT_NN" 
    
    HARD_MAX_LIMIT_LOTS = 5

    # Route A: Absolute Continuous N:N Balance 
    if MODE == "STRICT_NN":
        max_allowed_ce_lots = pe_lots
        max_allowed_pe_lots = ce_lots

    # Route B: Trend-Driven Asymmetry Matrix (Opposite-Side Base)
    else:
        if supertrend == "BULL":
            max_allowed_ce_lots = pe_lots + 1  # Calls can expand to Put Count + 1
            max_allowed_pe_lots = ce_lots      # Puts restricted to matching Call Count
        elif supertrend == "BEAR":
            max_allowed_pe_lots = ce_lots + 1  # Puts can expand to Call Count + 1
            max_allowed_ce_lots = pe_lots      # Calls restricted to matching Put Count
        else:
            max_allowed_ce_lots = pe_lots      # Flat NONE trend forces strict matching
            max_allowed_pe_lots = ce_lots

    # Safety structural absolute ceiling constraints
    max_allowed_ce_lots = min(max_allowed_ce_lots, HARD_MAX_LIMIT_LOTS)
    max_allowed_pe_lots = min(max_allowed_pe_lots, HARD_MAX_LIMIT_LOTS)

    return max_allowed_ce_lots, max_allowed_pe_lots




