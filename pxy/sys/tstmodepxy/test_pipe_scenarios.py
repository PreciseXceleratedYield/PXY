import sys
import unittest
from pathlib import Path

SYS_DIR = Path(__file__).resolve().parents[1]
if str(SYS_DIR) not in sys.path:
    sys.path.insert(0, str(SYS_DIR))

from tstmodepxy.pipescenarios import (
    engine_window_open,
    evaluate_pipe_gate_matrix,
    is_actual_market_hours,
)


class PipeScenarioTests(unittest.TestCase):
    def test_all_production_pipe_gates_match_expected_results(self):
        self.assertGreaterEqual(evaluate_pipe_gate_matrix(), 40)

    def test_chk_engine_is_blocked_only_during_weekday_market_hours(self):
        from datetime import datetime, timezone

        cases = (
            (datetime(2025, 1, 6, 9, 14), True),
            (datetime(2025, 1, 6, 9, 15), False),
            (datetime(2025, 1, 6, 15, 29), False),
            (datetime(2025, 1, 6, 15, 30), True),
            (datetime(2025, 1, 4, 12, 0), True),
            (datetime(2025, 1, 6, 3, 45, tzinfo=timezone.utc), False),
            (datetime(2025, 1, 6, 10, 0, tzinfo=timezone.utc), True),
        )
        for current_time, expected in cases:
            with self.subTest(current_time=current_time):
                self.assertEqual(engine_window_open(current_time), expected)

        self.assertFalse(
            is_actual_market_hours(
                datetime(2026, 1, 26, 10, 0),
                ("26-Jan-2026",),
            )
        )
