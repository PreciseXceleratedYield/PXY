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


def counter_leg_side(positions):
    """Return the one held option side that can be countered, if unambiguous."""
    position_counts = {"CE": 0, "PE": 0}
    for position in positions:
        symbol = str(position.get("symbol", "")).upper().strip()
        try:
            quantity = float(position.get("qty", 0) or 0)
        except (TypeError, ValueError):
            continue
        if not math.isfinite(quantity) or quantity <= 0:
            continue
        if symbol.endswith("CE"):
            position_counts["CE"] += 1
        elif symbol.endswith("PE"):
            position_counts["PE"] += 1

    has_ce = position_counts["CE"] > 0
    has_pe = position_counts["PE"] > 0

    if has_ce and not has_pe:
        return "CE"
    if has_pe and not has_ce:
        return "PE"
    return None


def counter_leg_script(exit_signal, positions, scripts):
    """Return the opposite-leg script when the exit signal opposes held exposure."""
    side = counter_leg_side(positions)
    signal = str(exit_signal).upper().strip()
    if side == "CE" and signal == "BEAR":
        return scripts["CE"]
    if side == "PE" and signal == "BULL":
        return scripts["PE"]
    return None


def averaging_trigger_sides(
    *,
    ce_aligned,
    pe_aligned,
    ce_rows,
    pe_rows,
    ce_investment=0.0,
    pe_investment=0.0,
    ce_cooling,
    pe_cooling,
    ce_loss,
    pe_loss,
    ce_threshold,
    pe_threshold,
    max_investment,
    ce_next_investment=0.0,
    pe_next_investment=0.0,
):
    """Return CE/PE averaging decisions using the placement pipe's exact gates.
    """
    both_sides_open_and_losing = (
        ce_rows > 0 and pe_rows > 0 and ce_loss < 0 and pe_loss < 0
    )
    ce_within_cap = ce_investment + ce_next_investment <= max_investment
    pe_within_cap = pe_investment + pe_next_investment <= max_investment

    return {
        "CE": bool(
            both_sides_open_and_losing
            and ce_aligned
            and not ce_cooling
            and ce_within_cap
            and ce_loss <= ce_threshold
        ),
        "PE": bool(
            both_sides_open_and_losing
            and pe_aligned
            and not pe_cooling
            and pe_within_cap
            and pe_loss <= pe_threshold
        ),
    }
