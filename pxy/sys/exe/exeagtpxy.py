"""
=============================================================================
STRATEGY MATH ENGINE LAYER: exeagtpxy.py (agt)
Contains ONLY pure atomic trading mathematical equations and trend alignments.
=============================================================================
"""

SYSTEM_A_BASE_THRESHOLD = 8.6
SYSTEM_B_BASE_THRESHOLD = 1.4
ABS_CAP = 77.0
BASE_COUNTER_TARGET_PCT = 4.1
FLOOR_BASE_POINTS = 140
FLOOR_STEP_POINTS = 100

def f(x, d=0.0):
    """Safely casts input to float, returning a default value if casting fails or value <= 0."""
    try:
        val = float(x)
        return val if val > 0 else d
    except (ValueError, TypeError):
        return d

def is_aligned(side, active_exit):
    """Core condition matching: CE aligns with BULL/SIDE, PE aligns with BEAR/SIDE."""
    a_exit = str(active_exit).upper().strip()
    s = side.upper()
    return (s == "CE" and a_exit in {"BULL"}) or (s == "PE" and a_exit in {"BEAR"})

def points_floor(lots):
    """Structural points floor calculation matrix based on position scaling."""
    return 0 if lots <= 0 else FLOOR_BASE_POINTS + FLOOR_STEP_POINTS * (lots - 1)

def getexeagtpxy(ce_invst_factor, pe_invst_factor, ce_lots, pe_lots):
    """Calculates investment-adjusted dynamic drawdown thresholds from capital weights."""
    ce_base = (SYSTEM_B_BASE_THRESHOLD * max(1, ce_lots)) + (SYSTEM_A_BASE_THRESHOLD * max(1, ce_lots)) * (ce_invst_factor ** 3)
    pe_base = (SYSTEM_B_BASE_THRESHOLD * max(1, pe_lots)) + (SYSTEM_A_BASE_THRESHOLD * max(1, pe_lots)) * (pe_invst_factor ** 3)
    return round((min(ce_base, ABS_CAP) * -1.0), 2), round((min(pe_base, ABS_CAP) * -1.0), 2)

def calculate_dynamic_target(side, active_exit, ce_investment, pe_investment):
    """Calculates target_pct based on trend alignment rules and capital weights."""
    if not is_aligned(side, active_exit):
        return BASE_COUNTER_TARGET_PCT
    ce_safe = ce_investment if ce_investment > 0 else 1.0
    pe_safe = pe_investment if pe_investment > 0 else 1.0
    factor = pe_safe / ce_safe if side.upper() == "CE" else ce_safe / pe_safe
    return BASE_COUNTER_TARGET_PCT + (BASE_COUNTER_TARGET_PCT * (factor ** 3))

def calculate_target_price_premium(entry_prc, target_pct):
    """Final mathematical target premium projection calculation."""
    return round(entry_prc * (1.0 + (target_pct / 100.0)), 2)

