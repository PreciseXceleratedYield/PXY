import sys
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

SYS_DIR = Path(__file__).resolve().parents[1]
if str(SYS_DIR) not in sys.path:
    sys.path.insert(0, str(SYS_DIR))

from tstmodepxy.pipescenarios import (
    SCENARIOS,
    engine_window_open,
    evaluate_scenario,
    evaluate_pipe_gate_matrix,
    is_actual_market_hours,
)
from tstmodepxy import mockproviders


class PipeScenarioTests(unittest.TestCase):
    def test_all_production_pipe_gates_match_expected_results(self):
        self.assertGreaterEqual(evaluate_pipe_gate_matrix(), 40)

    def test_all_expected_pipe_scenarios_pass(self):
        self.assertEqual(len(SCENARIOS), 10)
        for scenario in SCENARIOS:
            with self.subTest(scenario=scenario["name"]):
                result = evaluate_scenario(scenario)
                self.assertEqual(
                    set(result),
                    {"entry", "target_exit", "counter_leg", "averaging"},
                )

    def test_all_ledger_mock_scenarios_return_open_and_closed_dataframes(self):
        expected_columns = {
            "Scenario", "Symbol", "Qty", "Tag", "tok", "Buy_Time",
            "Buy_Prc", "Exit_Time", "Sell_Prc", "PNL",
        }
        for index, (name, _, _) in enumerate(mockproviders.MOCK_SCENARIOS):
            with self.subTest(scenario=name), redirect_stdout(StringIO()):
                open_rows, closed_rows = mockproviders.process_lilo_orders(
                    scenario_index=index
                )
            self.assertEqual(set(open_rows.columns), expected_columns)
            self.assertEqual(set(closed_rows.columns), expected_columns)
            self.assertTrue((open_rows["Exit_Time"] == "OPEN").all())
            self.assertTrue((closed_rows["Exit_Time"] != "OPEN").all())

    def test_chk_mock_gate_runs_every_scenario_not_minute_selected(self):
        output = StringIO()
        with redirect_stdout(output):
            self.assertTrue(mockproviders.skip_live_averaging())
        result = output.getvalue()
        self.assertIn("CHK PIPE SCENARIOS 10/10: PASS", result)
        for scenario in SCENARIOS:
            self.assertIn(scenario["name"], result)

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
