"""Pure pipe decisions shared by production execution and CHK scenario checks."""

import math
import re


def entry_signal_valid(signal):
    return isinstance(signal, str) and signal in ("BUY", "SELL")


def entry_blackout(now, preopen_start, preopen_end, cutoff, squareoff_end):
    return (
        preopen_start <= now < preopen_end
        or cutoff <= now < squareoff_end
    )


def entry_session_available(client):
    return client is not None


def parse_position_summary(position_summary):
    if not isinstance(position_summary, str):
        return None
    match = re.fullmatch(r"(\d+)CE(\d+)PE", position_summary.upper().strip())
    return (int(match.group(1)), int(match.group(2))) if match else None


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


def target_exit_allowed(market_snapshot_available, target, price, pnl, minimum_pnl):
    return bool(
        market_snapshot_available
        and target_exit_ready(target, price, pnl, minimum_pnl)
    )


def valid_exit_positions_response(response):
    return (
        isinstance(response, dict)
        and str(response.get("stat", "")).strip().lower() == "ok"
        and str(response.get("stCode", "")).strip() == "200"
        and isinstance(response.get("data"), list)
    )


def exit_order_response_accepted(response):
    return (
        isinstance(response, dict)
        and str(response.get("stat", "")).strip().lower() == "ok"
        and str(response.get("stCode", "")).strip() == "200"
    )


def averaging_order_response_accepted(response):
    if isinstance(response, dict):
        stat = str(response.get("stat", "")).lower()
        error = str(response.get("errMsg", "")).lower()
        if "failed" in stat or "error" in error or "error" in stat:
            return False
    return bool(response)


def matching_exit_net_quantity(positions, symbol, quantity_reader):
    matches = [position for position in positions if position.get("trdSym") == symbol]
    if not matches:
        return None
    return int(sum(quantity_reader(position) for position in matches))


def exit_quantity_to_sell(net_quantity, requested_quantity):
    try:
        net_quantity = int(net_quantity)
        requested_quantity = abs(int(float(requested_quantity)))
    except (TypeError, ValueError, OverflowError):
        return 0
    return min(net_quantity, requested_quantity) if net_quantity > 0 else 0


def exit_lock_recent(locks, key, seconds, now):
    if seconds <= 0:
        return False
    try:
        return now - float(locks.get(key, 0)) < seconds
    except (TypeError, ValueError):
        return False


def counter_leg_allowed(market_snapshot_available, positions_unverified, ledger_is_busy):
    return bool(
        market_snapshot_available
        and not positions_unverified
        and not ledger_is_busy
    )


def counter_leg_permission_status(
    now,
    cutoff,
    lock_is_recent,
    launches_today,
    daily_limit,
    action_enabled,
):
    if now >= cutoff:
        return "cutoff"
    if lock_is_recent:
        return "locked"
    if daily_limit > 0 and launches_today >= daily_limit:
        return "daily_limit"
    if not action_enabled:
        return "passive"
    return "allowed"


def averaging_snapshot_status(data_error, positions_unverified, has_active_rows):
    if data_error:
        return "error"
    if positions_unverified:
        return "positions_unverified"
    if not has_active_rows:
        return "empty"
    return "ready"


def averaging_window_enabled(rebuy_enabled, now, market_start, market_end):
    return bool(rebuy_enabled and market_start <= now < market_end)


def averaging_placement_allowed(ledger_is_busy):
    return not ledger_is_busy


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
    """Return CE/PE averaging decisions using the placement pipe's exact gates.
    
    Average ONLY when in LOSS (not when profitable).
    Trigger when loss exceeds the dynamic threshold.
    """
    return {
        "CE": bool(
            ce_aligned
            and ce_rows > 0
            and not ce_cooling
            and ce_rows < max_layers
            and ce_loss < 0  # ONLY when in LOSS
            and ce_loss <= ce_threshold  # Loss exceeds threshold
        ),
        "PE": bool(
            pe_aligned
            and pe_rows > 0
            and not pe_cooling
            and pe_rows < max_layers
            and pe_loss < 0  # ONLY when in LOSS
            and pe_loss <= pe_threshold  # Loss exceeds threshold
        ),
    }
