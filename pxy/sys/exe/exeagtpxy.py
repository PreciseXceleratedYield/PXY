# =============================================================================
# PURE DECISION MODULE: exetgtpxy.py
# TARGET / EXIT ALIGNMENT DECISION ENGINE (SYSTEM B)
# =============================================================================

ALIGNED_TARGET_PCT = 99.0
FLOOR_PCT = 1.4
FLOOR_BASE_POINTS = 140
FLOOR_STEP_POINTS = 100


def is_aligned(side, active_exit):
    """CE aligns with a BULL exit signal; PE aligns with a BEAR exit signal."""
    a_exit = str(active_exit).upper().strip()
    side = side.upper()
    if side == "CE":
        return a_exit == "BULL"
    if side == "PE":
        return a_exit == "BEAR"
    return False


def points_floor(lots):
    """140 for the first lot, +100 for each additional layer."""
    if lots <= 0:
        return 0
    return FLOOR_BASE_POINTS + FLOOR_STEP_POINTS * (lots - 1)


def decide(side, active_exit, avg_profit_pct, points_profit, lots,
           side_rows_empty, other_side_rows_empty, other_side_profit_pct, 
           other_side_points, other_side_lots):
    """
    Returns (decision, aligned) where decision is one of:
    "square_off", "fresh_buy", "hold"
    """
    aligned = is_aligned(side, active_exit)

    if aligned:
        if avg_profit_pct >= ALIGNED_TARGET_PCT:
            return "square_off", aligned
        return "hold", aligned

    # --- COUNTER-TREND / MISALIGNED TRACK ---
    floor = points_floor(lots)
    if avg_profit_pct >= FLOOR_PCT and points_profit >= floor:
        return "square_off", aligned

    # --- OPPOSITE SIDE FRESH BUY GATE ---
    # Intercept missing legs only if the open position cannot execute an exit
    if side_rows_empty and not other_side_rows_empty:
        other_floor = points_floor(other_side_lots)
        running_side_can_exit = (other_side_profit_pct >= FLOOR_PCT and other_side_points >= other_floor)
        
        if running_side_can_exit:
            return "hold", aligned
            
        return "fresh_buy", aligned

    return "hold", aligned
