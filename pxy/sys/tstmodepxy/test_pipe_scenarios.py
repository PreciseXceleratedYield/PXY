import sys
import unittest
from pathlib import Path

SYS_DIR = Path(__file__).resolve().parents[1]
if str(SYS_DIR) not in sys.path:
    sys.path.insert(0, str(SYS_DIR))

from tstmodepxy.pipescenarios import (
    SCENARIOS,
    engine_window_open,
    evaluate_pipe_gate_matrix,
    evaluate_scenario,
    selected_scenario_index,
)


class PipeScenarioTests(unittest.TestCase):
    def test_all_ten_scenarios_match_expected_pipe_decisions(self):
        self.assertEqual(len(SCENARIOS), 10)
        for index, scenario in enumerate(SCENARIOS):
            with self.subTest(scenario=index + 1, name=scenario["name"]):
                evaluate_scenario(scenario)

    def test_all_production_pipe_gates_match_expected_results(self):
        self.assertGreaterEqual(evaluate_pipe_gate_matrix(), 40)

    def test_minute_last_digit_selects_expected_scenario(self):
        for minute in range(60):
            with self.subTest(minute=minute):
                expected = (minute % 10) - 1 if minute % 10 else 9
                self.assertEqual(selected_scenario_index(minute), expected)

    def test_tst_engine_is_blocked_only_during_weekday_market_hours(self):
        from datetime import datetime

        cases = (
            (datetime(2025, 1, 6, 9, 15), True),
            (datetime(2025, 1, 6, 9, 16), False),
            (datetime(2025, 1, 6, 15, 29), False),
            (datetime(2025, 1, 6, 15, 30), True),
            (datetime(2025, 1, 4, 12, 0), True),
        )
        for current_time, expected in cases:
            with self.subTest(current_time=current_time):
                self.assertEqual(engine_window_open(current_time), expected)
