# =============================================================================
# UTILITY MODULE: exeagtpxy.py
# ISOLATED DYNAMIC DRAWDOWN THRESHOLD CALCULATOR
# =============================================================================

def exeagtpxy(atr, ce_invst_factor, pe_invst_factor, active_exit, super_trend):
    """Calculates direct investment-adjusted dynamic drawdown thresholds."""
    raw_val = atr * atr
    cepe_base_drawdown_limit = (max(16, min(raw_val, 76)) * -1)

    s_trend, a_exit = str(super_trend).upper(), str(active_exit).upper()

    # Two simple conditional assignment lines
    ce_trend_factor = 2.0 if s_trend == 'BEAR' and a_exit == 'BEAR' else 1.0
    pe_trend_factor = 2.0 if s_trend == 'BULL' and a_exit == 'BULL' else 1.0

    # Compute final dynamic drawdown thresholds
    ce_dynamic_threshold = cepe_base_drawdown_limit * ce_invst_factor * ce_invst_factor * ce_trend_factor
    pe_dynamic_threshold = cepe_base_drawdown_limit * pe_invst_factor * pe_invst_factor * pe_trend_factor

    return ce_dynamic_threshold, pe_dynamic_threshold
