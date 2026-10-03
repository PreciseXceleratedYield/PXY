import sys
import unittest
from datetime import datetime
from pathlib import Path

SYS_DIR = Path(__file__).resolve().parents[1]
if str(SYS_DIR) not in sys.path:
    sys.path.insert(0, str(SYS_DIR))

from tstmodepxy.pointbacktest import (
    is_actual_market_hours,
    simulate_point_session,
    simulate_point_trades,
)


class PointBacktestTests(unittest.TestCase):
    def test_ce_and_pe_points_follow_underlying_direction(self):
        bars = (
            {"timestamp": datetime(2025, 1, 6, 9, 16), "spot": 100, "entry": "BUY", "exit": "BULL", "next_timestamp": datetime(2025, 1, 6, 9, 17), "next_open": 101},
            {"timestamp": datetime(2025, 1, 6, 9, 17), "spot": 110, "entry": "NONE", "exit": "BEAR", "next_timestamp": datetime(2025, 1, 6, 9, 18), "next_open": 111},
            {"timestamp": datetime(2025, 1, 6, 9, 18), "spot": 100, "entry": "SELL", "exit": "BEAR", "next_timestamp": datetime(2025, 1, 6, 9, 19), "next_open": 99},
            {"timestamp": datetime(2025, 1, 6, 9, 19), "spot": 90, "entry": "NONE", "exit": "BULL", "next_timestamp": datetime(2025, 1, 6, 9, 20), "next_open": 89},
        )
        trades = simulate_point_trades(bars)
        self.assertEqual([trade["side"] for trade in trades], ["CE", "PE"])
        self.assertEqual([trade["points"] for trade in trades], [10, 10])
        self.assertEqual(
            (trades[0]["entry_time"], trades[0]["exit_time"]),
            (datetime(2025, 1, 6, 9, 17), datetime(2025, 1, 6, 9, 18)),
        )
        _, decisions = simulate_point_session(bars)
        self.assertEqual(decisions[0]["action"], "ENTRY_CE")
        self.assertEqual(decisions[1]["action"], "EXIT_SIGNAL_PROXY")
        self.assertEqual(decisions[0]["next_bar_open"], 101)

    def test_production_entry_cutoff_is_applied(self):
        bars = (
            {"timestamp": datetime(2025, 1, 6, 15, 10), "spot": 100, "entry": "BUY", "exit": "BULL", "next_timestamp": datetime(2025, 1, 6, 15, 11), "next_open": 101},
        )
        trades, decisions = simulate_point_session(bars)
        self.assertEqual(trades, [])
        self.assertEqual(decisions[0]["action"], "NO_ENTRY_BLACKOUT")

    def test_squareoff_closes_trade_and_does_not_carry_overnight(self):
        bars = (
            {"timestamp": datetime(2025, 1, 6, 15, 9), "spot": 100, "entry": "BUY", "exit": "BULL", "next_timestamp": datetime(2025, 1, 6, 15, 10), "next_open": 101},
            {"timestamp": datetime(2025, 1, 6, 15, 14), "spot": 95, "entry": "BUY", "exit": "BULL", "next_timestamp": datetime(2025, 1, 6, 15, 15), "next_open": 96},
        )
        trades = simulate_point_trades(bars)
        self.assertEqual(len(trades), 1)
        self.assertEqual(trades[0]["points"], -6)
        self.assertEqual(trades[0]["exit_reason"], "end_of_day")

    def test_market_hours_guard_uses_ist_and_holidays(self):
        cases = (
            (datetime(2025, 1, 6, 10, 0), (), True),
            (datetime(2025, 1, 6, 10, 0), ("06-Jan-2025",), False),
            (datetime(2025, 1, 4, 10, 0), (), False),
            (datetime(2025, 1, 6, 8, 0), (), False),
        )
        for current, holidays, expected in cases:
            with self.subTest(current=current, holidays=holidays):
                self.assertEqual(is_actual_market_hours(current, holidays), expected)
