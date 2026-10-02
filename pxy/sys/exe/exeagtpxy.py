"""
=============================================================================
STRATEGY MATH ENGINE LAYER: exeagtpxy.py (agt)
Contains ONLY the averaging (System A) threshold math and trend alignment.
=============================================================================
"""

from syscnfgpxy import (
    EXEAGTPXY_ABS_CAP,
    EXEAGTPXY_FORCE_DEFAULT,
    EXEAGTPXY_SYSTEM_A_BASE_THRESHOLD,
    EXEAGTPXY_SYSTEM_B_BASE_THRESHOLD,
)

SYSTEM_A_BASE_THRESHOLD = EXEAGTPXY_SYSTEM_A_BASE_THRESHOLD
SYSTEM_B_BASE_THRESHOLD = EXEAGTPXY_SYSTEM_B_BASE_THRESHOLD
ABS_CAP = EXEAGTPXY_ABS_CAP

def is_aligned(side, active_exit):
    """Core condition matching: CE aligns ONLY with BULL, PE aligns ONLY with BEAR.
    SIDE / NONE / anything else is not aligned (averaging stays off)."""
    a_exit = str(active_exit).upper().strip()
    s = side.upper()
    return (s == "CE" and a_exit in {"BULL"}) or (s == "PE" and a_exit in {"BEAR"})

FORCE_DEFAULT = EXEAGTPXY_FORCE_DEFAULT


def _clean_force(v):
    """A force that is missing, NaN, non-numeric or negative falls back to FORCE_DEFAULT.
    A negative force would flip the threshold positive and make averaging fire every cooldown."""
    try:
        v = float(v)
    except (TypeError, ValueError):
        return FORCE_DEFAULT
    if v != v or v < 0:
        return FORCE_DEFAULT
    return v


def _threshold(invst_factor, lots, force):
    base = (SYSTEM_B_BASE_THRESHOLD * max(1, lots)) + \
           (SYSTEM_A_BASE_THRESHOLD * max(1, lots)) * (max(0.0, invst_factor) ** 3) * force
    # always a negative number, never tighter than the B base and never deeper than ABS_CAP
    base = min(max(base, SYSTEM_B_BASE_THRESHOLD), ABS_CAP)
    return round(base * -1.0, 2)


def getexeagtpxy(ce_invst_factor, pe_invst_factor, ce_lots, pe_lots, ce_force, pe_force):
    """Calculates investment-adjusted dynamic drawdown thresholds from capital weights and ADX force vectors.
    Always returns two negative thresholds in [-ABS_CAP, -SYSTEM_B_BASE_THRESHOLD]."""
    ce_thr = _threshold(ce_invst_factor, ce_lots, _clean_force(ce_force))
    pe_thr = _threshold(pe_invst_factor, pe_lots, _clean_force(pe_force))
    return ce_thr, pe_thr
