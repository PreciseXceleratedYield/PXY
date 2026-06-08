#execepepxy.py
def get_target_quantities(supertrend, ce_qty, pe_qty, lot_size):
    """
    Calculates the allowed target quantities based on supertrend bias.
    Maintains an N+1 lot structure for the favored side.
    """
    if not lot_size:
        return ce_qty, pe_qty

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

    return max_allowed_ce, max_allowed_pe
