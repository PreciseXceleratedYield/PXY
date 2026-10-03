"""Expected, deterministic pipe decisions for the ten TST minute scenarios."""

from datetime import time

from sysdecisionpxy import (
    averaging_trigger_sides,
    counter_leg_script,
    entry_order_command,
    target_exit_ready,
)


def engine_window_open(now):
    """TST engine is permitted only outside weekday market hours (09:16-15:30 IST)."""
    market_open = (
        now.weekday() < 5
        and time(9, 16) <= now.time().replace(tzinfo=None) < time(15, 30)
    )
    return not market_open


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
        "average": (False, False, 0, 1, False, False, 0, -9, -2, -2, 5, {"CE": False, "PE": False}),
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


def evaluate_scenario(scenario):
    signal, ce_lots, pe_lots, expected_entry = scenario["entry"]
    actual_entry = entry_order_command(signal, ce_lots, pe_lots)

    target, price, pnl, minimum_pnl, expected_exit = scenario["target"]
    actual_exit = target_exit_ready(target, price, pnl, minimum_pnl)

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


def selected_scenario_index(minute):
    """Map IST minute endings :01-:09 to scenarios 1-9 and :00 to scenario 10."""
    return (minute % 10) - 1 if minute % 10 else 9
