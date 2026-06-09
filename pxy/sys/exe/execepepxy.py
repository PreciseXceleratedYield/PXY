def get_target_quantities(supertrend, ce_qty, pe_qty, lot_size):
    """
    Calculates the allowed target quantities based on supertrend bias.
    Maintains an N+1 lot structure for the favored side up to a hard max of 8.
    """
    HARD_MAX_LIMIT = 8

    # Edge case: No lot size or invalid values
    if not lot_size or lot_size <= 0:
        return min(ce_qty, HARD_MAX_LIMIT), min(pe_qty, HARD_MAX_LIMIT)

    # 1. Determine the core baseline 'N' based on the largest current position
    current_max = max(ce_qty, pe_qty)
    
    # 2. Derive the base lot size (clamped to ensure it doesn't exceed the hard limit)
    base_lots = min(current_max, HARD_MAX_LIMIT)

    # 3. Set standard neutral limits
    max_allowed_ce = base_lots
    max_allowed_pe = base_lots

    # 4. Apply structural asymmetry based on bias
    if supertrend == "BULL":
        # CE gets the extra lot, PE is capped at the base structural level
        max_allowed_ce = base_lots + lot_size
        max_allowed_pe = max(0, max_allowed_ce - lot_size)
    elif supertrend == "BEAR":
        # PE gets the extra lot, CE is capped at the base structural level
        max_allowed_pe = base_lots + lot_size
        max_allowed_ce = max(0, max_allowed_pe - lot_size)

    # 5. Enforce strict final boundary limits
    max_allowed_ce = min(max_allowed_ce, HARD_MAX_LIMIT)
    max_allowed_pe = min(max_allowed_pe, HARD_MAX_LIMIT)

    return max_allowed_ce, max_allowed_pe


