"""Pure pipe decisions shared by production execution and TST scenario checks."""

import math


def entry_order_command(signal, ce_lots, pe_lots):
    """Return the fresh-entry command only for a valid signal and a flat account."""
    normalized = str(signal).upper().strip()
    if ce_lots != 0 or pe_lots != 0:
        return None
    if normalized == "BUY":
        return "pxybuyce"
    if normalized == "SELL":
        return "pxybuype"
    return None


def target_exit_ready(target, price, pnl, minimum_pnl):
    """Return whether the exit pipe's target and minimum-P&L gates both pass."""
    try:
        target, price, pnl, minimum_pnl = map(
            float, (target, price, pnl, minimum_pnl)
        )
    except (TypeError, ValueError):
        return False
    if not all(map(math.isfinite, (target, price, pnl, minimum_pnl))):
        return False
    return target > 0 and price > 0 and price >= target and pnl >= minimum_pnl


def counter_leg_script(exit_state, positions, scripts):
    """Return the counter-leg script for a hostile one-sided position, else None."""
    state = str(exit_state).upper().strip()
    if state not in {"BULL", "BEAR"}:
        return None

    has_ce = has_pe = False
    for position in positions:
        symbol = str(position.get("symbol", "")).upper().strip()
        try:
            quantity = float(position.get("qty", 0) or 0)
        except (TypeError, ValueError):
            continue
        if not math.isfinite(quantity) or quantity <= 0:
            continue
        has_ce = has_ce or symbol.endswith("CE")
        has_pe = has_pe or symbol.endswith("PE")

    if state == "BEAR" and has_ce and not has_pe:
        return scripts["CE"]
    if state == "BULL" and has_pe and not has_ce:
        return scripts["PE"]
    return None


def averaging_trigger_sides(
    *,
    ce_aligned,
    pe_aligned,
    ce_rows,
    pe_rows,
    ce_cooling,
    pe_cooling,
    ce_loss,
    pe_loss,
    ce_threshold,
    pe_threshold,
    max_layers,
):
    """Return CE/PE averaging decisions using the placement pipe's exact gates."""
    return {
        "CE": bool(
            ce_aligned
            and ce_rows > 0
            and not ce_cooling
            and ce_rows < max_layers
            and ce_loss <= ce_threshold
        ),
        "PE": bool(
            pe_aligned
            and pe_rows > 0
            and not pe_cooling
            and pe_rows < max_layers
            and pe_loss <= pe_threshold
        ),
    }
