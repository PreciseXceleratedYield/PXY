def get_target_quantities(supertrend, ce_qty, pe_qty, lot_size):
    """
    Calculates the allowed target quantities based on supertrend bias.
    Maintains an N+1 lot structure for the favored side up to a hard max of 6.
    """
    # Enforce a hard maximum risk limit across the entire system
    HARD_MAX_LIMIT = 8

    if not lot_size:
        # If no lot size, clamp current quantities to the hard limit
        return min(pe_qty, HARD_MAX_LIMIT), min(ce_qty, HARD_MAX_LIMIT)

    # Default limits allow them to be perfectly equal
    max_allowed_ce = pe_qty
    max_allowed_pe = ce_qty

    # Adjust limits based on the dominant supertrend structure
    if supertrend == "BULL":
        # CE is favored to be N + 1 lot ahead of PE
        max_allowed_ce = pe_qty + lot_size
    elif supertrend == "BEAR":
        # PE is favored to be N + 1 lot ahead of CE
        max_allowed_pe = ce_qty + lot_size

    # Cap both sides strictly at your maximum limit of 6
    max_allowed_ce = min(max_allowed_ce, HARD_MAX_LIMIT)
    max_allowed_pe = min(max_allowed_pe, HARD_MAX_LIMIT)

    return max_allowed_ce, max_allowed_pe

