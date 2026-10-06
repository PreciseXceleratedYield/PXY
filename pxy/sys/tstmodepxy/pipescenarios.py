"""Expected, deterministic pipe decisions for the ten CHK minute scenarios."""

from datetime import time

from sysdecisionpxy import (
    averaging_order_response_accepted,
    averaging_placement_allowed,
    averaging_snapshot_status,
    averaging_trigger_sides,
    averaging_window_enabled,
    counter_leg_script,
    counter_leg_allowed,
    counter_leg_permission_status,
    entry_blackout,
    entry_order_command,
    entry_session_available,
    entry_signal_valid,
    exit_quantity_to_sell,
    exit_lock_recent,
    exit_order_response_accepted,
    matching_exit_net_quantity,
    target_exit_allowed,
    target_exit_ready,
    parse_position_summary,
    valid_exit_positions_response,
)
from .pointbacktest import is_actual_market_hours


SCENARIOS = (
    {
        "name": "BUY flat, CE target, BEAR counter, CE average",
        "entry": ("BUY", 0, 0, "pxybuyce"),
        "target": (110, 120, 180, 150, True),
        "counter": ("BEAR", ({"symbol": "NIFTYCE", "qty": 1},), "pxybuype"),
        "average": (True, False, 1, 0, False, False, -3, 0, -2, -2, 5, {"CE": True, "PE": False}),
    },
    {
        "name": "SELL flat, PE counter and average, target miss",
        "entry": ("SELL", 0, 0, "pxybuype"),
        "target": (110, 109, 200, 150, False),
        "counter": ("BULL", ({"symbol": "NIFTYPE", "qty": 2},), "pxybuyce"),
        "average": (False, True, 0, 1, False, False, 0, -4, -2, -2, 5, {"CE": False, "PE": True}),
    },
    {
        "name": "occupied CE blocks fresh BUY, averaging cooldown",
        "entry": ("BUY", 1, 0, None),
        "target": (100, 120, 149, 150, False),
        "counter": ("SIDE", ({"symbol": "NIFTYCE", "qty": 1},), None),
        "average": (True, True, 1, 1, True, False, -5, -5, -2, -2, 5, {"CE": False, "PE": True}),
    },
    {
        "name": "invalid HOLD, target boundary, balanced legs",
        "entry": ("HOLD", 0, 0, None),
        "target": (100, 100, 150, 150, True),
        "counter": ("BEAR", ({"symbol": "NIFTYCE", "qty": 1}, {"symbol": "NIFTYPE", "qty": 1}), None),
        "average": (True, True, 1, 1, False, False, -2, -2, -2, -2, 5, {"CE": True, "PE": True}),
    },
    {
        "name": "BUY flat, target miss, PE counter, both averages",
        "entry": ("BUY", 0, 0, "pxybuyce"),
        "target": (101, 100, 200, 150, False),
        "counter": ("BULL", ({"symbol": "NIFTYPE", "qty": 1},), "pxybuyce"),
        "average": (True, True, 2, 3, False, False, -3, -4, -2, -2, 5, {"CE": True, "PE": True}),
    },
    {
        "name": "open PE blocks SELL, PE at max layers",
        "entry": ("SELL", 0, 2, None),
        "target": (100, 110, 149, 150, False),
        "counter": ("BEAR", ({"symbol": "NIFTYPE", "qty": 2},), None),
        "average": (False, True, 0, 5, False, False, 0, -8, -2, -2, 5, {"CE": False, "PE": False}),
    },
    {
        "name": "zero-quantity leg ignored; CE max layers",
        "entry": ("BUY", 0, 0, "pxybuyce"),
        "target": (120, 121, 500, 150, True),
        "counter": ("BEAR", ({"symbol": "NIFTYCE", "qty": 0},), None),
        "average": (True, False, 5, 0, False, False, -8, 0, -2, -2, 5, {"CE": False, "PE": False}),
    },
    {
        "name": "NONE signal, BULL PE counter, unaligned average",
        "entry": ("NONE", 0, 0, None),
        "target": (0, 100, 500, 150, False),
        "counter": ("BULL", ({"symbol": "NIFTYPE", "qty": 1},), "pxybuyce"),
        "average": (False, False, 0, 1, False, False, 0, -9, -2, -2, 5, {"CE": False, "PE": True}),
    },
    {
        "name": "BUY flat target, PE averaging at loss threshold",
        "entry": ("BUY", 0, 0, "pxybuyce"),
        "target": (100, 100, 150, 150, True),
        "counter": ("BULL", ({"symbol": "NIFTYCE", "qty": 1},), None),
        "average": (False, True, 0, 2, False, False, 0, -2, -2, -2, 5, {"CE": False, "PE": True}),
    },
    {
        "name": "SELL flat, BULL PE counter, cooldown blocks averaging",
        "entry": ("SELL", 0, 0, "pxybuype"),
        "target": (110, 112, 151, 150, True),
        "counter": ("BULL", ({"symbol": "NIFTYPE", "qty": 1},), "pxybuyce"),
        "average": (True, True, 1, 1, True, True, -8, -8, -2, -2, 5, {"CE": False, "PE": False}),
    },
)


def engine_window_open(now, market_holidays=()):
    return not is_actual_market_hours(now, market_holidays)


def evaluate_scenario(scenario):
    signal, ce_lots, pe_lots, expected_entry = scenario["entry"]
    actual_entry = entry_order_command(signal, ce_lots, pe_lots)

    target, price, pnl, minimum_pnl, expected_exit = scenario["target"]
    actual_exit = target_exit_allowed(True, target, price, pnl, minimum_pnl)

    exit_state, positions, expected_counter = scenario["counter"]
    actual_counter = counter_leg_script(
        exit_state,
        positions,
        {"CE": "pxybuype", "PE": "pxybuyce"},
    )

    (
        ce_aligned, pe_aligned, ce_rows, pe_rows, ce_cooling, pe_cooling,
        ce_loss, pe_loss, ce_threshold, pe_threshold, max_layers, expected_average,
    ) = scenario["average"]
    actual_average = averaging_trigger_sides(
        ce_aligned=ce_aligned,
        pe_aligned=pe_aligned,
        ce_rows=ce_rows,
        pe_rows=pe_rows,
        ce_cooling=ce_cooling,
        pe_cooling=pe_cooling,
        ce_loss=ce_loss,
        pe_loss=pe_loss,
        ce_threshold=ce_threshold,
        pe_threshold=pe_threshold,
        max_layers=max_layers,
    )

    actual = {
        "entry": actual_entry,
        "target_exit": actual_exit,
        "counter_leg": actual_counter,
        "averaging": actual_average,
    }
    expected = {
        "entry": expected_entry,
        "target_exit": expected_exit,
        "counter_leg": expected_counter,
        "averaging": expected_average,
    }
    if actual != expected:
        raise AssertionError(
            f"{scenario['name']}: expected {expected!r}, got {actual!r}"
        )
    return actual


def evaluate_pipe_gate_matrix():
    cases = (
        ("entry BUY signal", lambda: entry_signal_valid("BUY"), True),
        ("entry SELL signal", lambda: entry_signal_valid("SELL"), True),
        ("entry invalid signal", lambda: entry_signal_valid("HOLD"), False),
        ("entry missing signal", lambda: entry_signal_valid(None), False),
        ("entry before preopen blackout", lambda: entry_blackout(time(9, 13), time(9, 14), time(9, 16), time(15, 10), time(15, 50)), False),
        ("entry preopen blackout", lambda: entry_blackout(time(9, 15), time(9, 14), time(9, 16), time(15, 10), time(15, 50)), True),
        ("entry cutoff boundary", lambda: entry_blackout(time(15, 10), time(9, 14), time(9, 16), time(15, 10), time(15, 50)), True),
        ("entry after cutoff window", lambda: entry_blackout(time(15, 50), time(9, 14), time(9, 16), time(15, 10), time(15, 50)), False),
        ("entry missing session", lambda: entry_session_available(None), False),
        ("entry session available", lambda: entry_session_available(object()), True),
        ("entry valid position summary", lambda: parse_position_summary("1CE2PE"), (1, 2)),
        ("entry formatted position summary", lambda: parse_position_summary(" 0ce0pe "), (0, 0)),
        ("entry malformed position summary", lambda: parse_position_summary("unknown"), None),
        ("entry non-string position summary", lambda: parse_position_summary(None), None),
        ("entry BUY flat", lambda: entry_order_command("BUY", 0, 0), "pxybuyce"),
        ("entry SELL flat", lambda: entry_order_command("SELL", 0, 0), "pxybuype"),
        ("entry occupied CE", lambda: entry_order_command("BUY", 1, 0), None),
        ("entry occupied PE", lambda: entry_order_command("SELL", 0, 1), None),
        ("exit target, price and PnL pass", lambda: target_exit_ready(100, 100, 150, 150), True),
        ("exit target disabled", lambda: target_exit_ready(0, 100, 500, 150), False),
        ("exit invalid price", lambda: target_exit_ready(100, 0, 500, 150), False),
        ("exit price below target", lambda: target_exit_ready(100, 99, 500, 150), False),
        ("exit PnL below minimum", lambda: target_exit_ready(100, 110, 149, 150), False),
        ("exit non-finite price", lambda: target_exit_ready(100, float("nan"), 500, 150), False),
        ("exit malformed value", lambda: target_exit_ready(100, "bad", 500, 150), False),
        ("exit snapshot missing", lambda: target_exit_allowed(False, 100, 110, 500, 150), False),
        ("exit snapshot available", lambda: target_exit_allowed(True, 100, 110, 500, 150), True),
        ("exit invalid positions response", lambda: valid_exit_positions_response(None), False),
        ("exit unsuccessful positions response", lambda: valid_exit_positions_response({"stat": "Not_Ok", "stCode": "200", "data": []}), False),
        ("exit bad response code", lambda: valid_exit_positions_response({"stat": "Ok", "stCode": "500", "data": []}), False),
        ("exit missing response data", lambda: valid_exit_positions_response({"stat": "Ok", "stCode": "200"}), False),
        ("exit valid positions response", lambda: valid_exit_positions_response({"stat": "Ok", "stCode": "200", "data": []}), True),
        ("exit accepted order response", lambda: exit_order_response_accepted({"stat": "Ok", "stCode": "200"}), True),
        ("exit rejected order response", lambda: exit_order_response_accepted({"stat": "Ok", "stCode": "500"}), False),
        ("exit malformed order response", lambda: exit_order_response_accepted("accepted"), False),
        ("exit positions symbol not found", lambda: matching_exit_net_quantity([], "NIFTYCE", lambda row: row["net_qty"]), None),
        ("exit matching positive broker net", lambda: matching_exit_net_quantity([{"trdSym": "NIFTYCE", "net_qty": 3}], "NIFTYCE", lambda row: row["net_qty"]), 3),
        ("exit matching nonpositive broker net", lambda: matching_exit_net_quantity([{"trdSym": "NIFTYCE", "net_qty": -1}], "NIFTYCE", lambda row: row["net_qty"]), -1),
        ("exit requested qty capped to broker net", lambda: exit_quantity_to_sell(2, 5), 2),
        ("exit requested qty respected", lambda: exit_quantity_to_sell(5, 2), 2),
        ("exit zero broker net", lambda: exit_quantity_to_sell(0, 2), 0),
        ("exit invalid requested qty", lambda: exit_quantity_to_sell(2, "bad"), 0),
        ("exit recent lock", lambda: exit_lock_recent({"order": 95}, "order", 10, 100), True),
        ("exit expired lock", lambda: exit_lock_recent({"order": 80}, "order", 10, 100), False),
        ("exit disabled lock", lambda: exit_lock_recent({"order": 99}, "order", 0, 100), False),
        ("counter-buy missing market data", lambda: counter_leg_allowed(False, False, False), False),
        ("counter-buy unverified positions", lambda: counter_leg_allowed(True, True, False), False),
        ("counter-buy ledger locked", lambda: counter_leg_allowed(True, False, True), False),
        ("counter-buy all gates pass", lambda: counter_leg_allowed(True, False, False), True),
        ("counter-buy cutoff", lambda: counter_leg_permission_status(time(15, 10), time(15, 10), False, 0, 6, True), "cutoff"),
        ("counter-buy recent duplicate lock", lambda: counter_leg_permission_status(time(14), time(15, 10), True, 0, 6, True), "locked"),
        ("counter-buy daily limit", lambda: counter_leg_permission_status(time(14), time(15, 10), False, 6, 6, True), "daily_limit"),
        ("counter-buy passive action", lambda: counter_leg_permission_status(time(14), time(15, 10), False, 0, 6, False), "passive"),
        ("counter-buy launch permitted", lambda: counter_leg_permission_status(time(14), time(15, 10), False, 0, 6, True), "allowed"),
        ("averaging data error", lambda: averaging_snapshot_status(True, False, True), "error"),
        ("averaging positions unverified", lambda: averaging_snapshot_status(False, True, True), "positions_unverified"),
        ("averaging no active rows", lambda: averaging_snapshot_status(False, False, False), "empty"),
        ("averaging snapshot ready", lambda: averaging_snapshot_status(False, False, True), "ready"),
        ("averaging rebuy disabled", lambda: averaging_window_enabled(False, time(10), time(9, 17), time(15, 10)), False),
        ("averaging before window", lambda: averaging_window_enabled(True, time(9, 16), time(9, 17), time(15, 10)), False),
        ("averaging window opens", lambda: averaging_window_enabled(True, time(9, 17), time(9, 17), time(15, 10)), True),
        ("averaging window closes", lambda: averaging_window_enabled(True, time(15, 10), time(9, 17), time(15, 10)), False),
        ("averaging ledger lock", lambda: averaging_placement_allowed(True), False),
        ("averaging ledger clear", lambda: averaging_placement_allowed(False), True),
        ("averaging accepted order response", lambda: averaging_order_response_accepted({"stat": "Ok"}), True),
        ("averaging rejected order response", lambda: averaging_order_response_accepted({"stat": "failed"}), False),
        ("averaging broker error response", lambda: averaging_order_response_accepted({"errMsg": "order error"}), False),
        ("averaging empty order response", lambda: averaging_order_response_accepted(None), False),
    )
    failures = []
    for name, check, expected in cases:
        try:
            actual = check()
            if actual != expected:
                failures.append(
                    f"{name}: expected {expected!r}, got {actual!r}"
                )
        except Exception as error:
            failures.append(f"{name}: raised {error!r}")
    if failures:
        raise AssertionError("; ".join(failures))
    return len(cases)


def selected_scenario_index(minute):
    """Map IST minute endings :01-:09 to scenarios 1-9 and :00 to scenario 10."""
    return (minute % 10) - 1 if minute % 10 else 9
