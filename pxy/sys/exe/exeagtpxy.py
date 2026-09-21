# =============================================================================
# STRATEGY INTEGRATION LAYER: exeagtpxy.py (agt)
# CORE MATHEMATICAL MODELLING ENGINE FOR SYSTEM A AND CRITICAL ALIGNMENTS
# =============================================================================
import logging
from colorama import Fore

# MAPPED TO ACG CORE INFRASTRUCTURE FRAMEWORK FILE
from exeacgpxy import (
    MAX_LAYERS, safe_float, generate_pxy_tag, is_cooling, set_cooling,
    print_pxy_trigger_dashboard
)

logger = logging.getLogger("exeavgpxy.strategy")

# -----------------------------------------------------------------------------
# 📊 SECTION 1: SYSTEM A THRESHOLD PROCESSING & PLACEMENT LOGIC
# -----------------------------------------------------------------------------
SYSTEM_A_BASE_THRESHOLD = 5
SYSTEM_B_BASE_THRESHOLD = 0.0
ABS_CAP = 77.0


def getexeagtpxy(ce_invst_factor, pe_invst_factor, ce_lots, pe_lots):
    """Calculates investment-adjusted dynamic drawdown thresholds from capital weights."""
    # Using max(1, lots) ensures that the baseline threshold is 10.0% even when lots are 0
    ce_base_invested = SYSTEM_A_BASE_THRESHOLD + (SYSTEM_A_BASE_THRESHOLD * max(1, ce_lots)) * ce_invst_factor * ce_invst_factor * ce_invst_factor
    pe_base_invested = SYSTEM_A_BASE_THRESHOLD + (SYSTEM_A_BASE_THRESHOLD * max(1, pe_lots)) * pe_invst_factor * pe_invst_factor * pe_invst_factor

    ce_final_abs = (min(ce_base_invested, ABS_CAP) * -1.0) + SYSTEM_B_BASE_THRESHOLD
    pe_final_abs = (min(pe_base_invested, ABS_CAP) * -1.0) + SYSTEM_B_BASE_THRESHOLD

    return round(ce_final_abs , 2), round(pe_final_abs, 2)



def execute_side_averaging_matrix(client, ce_rows, pe_rows, ce_lgt_val, pe_lgt_val,
                                  ce_dynamic_threshold, pe_dynamic_threshold, ce_lots, pe_lots,
                                  ce_aligned, pe_aligned):
    """Executes network orders for System A when pullback boundaries are breached."""

    # 🟢 CALL OPTION (CE) SIDE LAYER GATEWAY
    if ce_aligned and not ce_rows.empty and not is_cooling("CE") and len(ce_rows) < (MAX_LAYERS + 1):
        ce_last_row = ce_rows.iloc[-1]
        ce_symbol = ce_last_row['symbol']
        ce_qty = abs(int(safe_float(ce_last_row.get('qty', 0.0))))

        if ce_lgt_val <= ce_dynamic_threshold:
            logger.info(f"⚖️ CE TRIGGERED: Metric Value ({ce_lgt_val}%) <= Threshold ({ce_dynamic_threshold}%).")
            try:
                new_tag = generate_pxy_tag()
                print_pxy_trigger_dashboard("CE", ce_symbol, ce_lgt_val, ce_dynamic_threshold, new_tag, ce_lots, pe_lots, "AUTO")
                params = {
                    "exchange_segment": "nse_fo", "product": "NRML", "price": "0", "order_type": "MKT",
                    "quantity": str(ce_qty), "trading_symbol": str(ce_symbol), "transaction_type": "B",
                    "validity": "DAY", "amo": "NO", "tag": new_tag
                }
                set_cooling("CE")
                if client.place_order(**params):
                    print(f"{Fore.GREEN}✅ SUCCESS: CE Averaged. Tag: {new_tag}")
            except Exception as e:
                logger.error(f"CE Native placement tracking error: {e}", exc_info=True)

    # 🔴 PUT OPTION (PE) SIDE LAYER GATEWAY
    if pe_aligned and not pe_rows.empty and not is_cooling("PE") and len(pe_rows) < (MAX_LAYERS + 1):
        pe_last_row = pe_rows.iloc[-1]
        pe_symbol = pe_last_row['symbol']
        pe_qty = abs(int(safe_float(pe_last_row.get('qty', 0.0))))

        if pe_lgt_val <= pe_dynamic_threshold:
            logger.info(f"⚖️ PE TRIGGERED: Metric Value ({pe_lgt_val}%) <= Threshold ({pe_dynamic_threshold}%).")
            try:
                new_tag = generate_pxy_tag()
                print_pxy_trigger_dashboard("PE", pe_symbol, pe_lgt_val, pe_dynamic_threshold, new_tag, ce_lots, pe_lots, "AUTO")
                params = {
                    "exchange_segment": "nse_fo", "product": "NRML", "price": "0", "order_type": "MKT",
                    "quantity": str(pe_qty), "trading_symbol": str(pe_symbol), "transaction_type": "B",
                    "validity": "DAY", "amo": "NO", "tag": new_tag
                }
                set_cooling("PE")
                if client.place_order(**params):
                    print(f"{Fore.GREEN}✅ SUCCESS: PE Averaged. Tag: {new_tag}")
            except Exception as e:
                logger.error(f"PE Native placement tracking error: {e}", exc_info=True)


# -----------------------------------------------------------------------------
# 📈 SECTION 2: SYSTEM B RULE MATRIX (TARGET SELECTION ENGINE)
# -----------------------------------------------------------------------------
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


def can_exit(side, active_exit, profit_pct, points_profit, lots):
    """True if this side's OWN real target condition is currently met —
    99% if aligned, 1.4%+points-floor if not. Used to check whether the
    OPPOSITE side is already good to flatten before firing a fresh buy."""
    if is_aligned(side, active_exit):
        return profit_pct >= ALIGNED_TARGET_PCT
    return profit_pct >= FLOOR_PCT and points_profit >= points_floor(lots)


def decide(side, active_exit, avg_profit_pct, points_profit, lots,
           side_rows_empty, other_side_rows_empty, other_side_profit_pct,
           other_side_points, other_side_lots):
    """Returns (decision, aligned) — single-action-per-iteration guaranteed."""
    aligned = is_aligned(side, active_exit)

    if aligned:
        if avg_profit_pct >= ALIGNED_TARGET_PCT:
            return "square_off", aligned
        return "hold", aligned

    # --- NOT ALIGNED: force-exit check first ---
    floor = points_floor(lots)
    if avg_profit_pct >= FLOOR_PCT and points_profit >= floor:
        return "square_off", aligned

    # --- Bad luck: floor not cleared. Fill missing leg only if the
    #     running side isn't already about to exit on its own real target. ---
    if side_rows_empty and not other_side_rows_empty:
        other_side = "PE" if side == "CE" else "CE"
        if can_exit(other_side, active_exit, other_side_profit_pct, other_side_points, other_side_lots):
            return "hold", aligned
        return "fresh_buy", aligned

    return "hold", aligned
