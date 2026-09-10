# =============================================================================
# UTILITY MODULE: exeagtpxy.py
# ISOLATED DYNAMIC DRAWDOWN THRESHOLD CALCULATOR
# =============================================================================

def exeagtpxy(atr, ce_invst_factor, pe_invst_factor):
    """Calculates direct investment-adjusted dynamic drawdown thresholds."""
    raw_val = atr * atr
    cepe_base_drawdown_limit = (max(16, min(raw_val, 76)) * -1)

    ce_dynamic_threshold = cepe_base_drawdown_limit * ce_invst_factor * ce_invst_factor
    pe_dynamic_threshold = cepe_base_drawdown_limit * pe_invst_factor * pe_invst_factor

    return ce_dynamic_threshold, pe_dynamic_threshold
