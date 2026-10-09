import sys
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

SYS_DIR = Path(__file__).resolve().parents[1]
if str(SYS_DIR) not in sys.path:
    sys.path.insert(0, str(SYS_DIR))

from tstmodepxy import checksim


class CheckSimTests(unittest.TestCase):
    def test_select_session_uses_one_based_menu_choices(self):
        sessions = [
            date(2026, 10, 9),
            date(2026, 10, 8),
            date(2026, 10, 7),
        ]
        self.assertEqual(checksim.select_session(sessions, "1"), sessions[0])
        self.assertEqual(checksim.select_session(sessions, "3"), sessions[2])
        self.assertIsNone(checksim.select_session(sessions, "0"))
        self.assertIsNone(checksim.select_session(sessions, "4"))
        self.assertIsNone(checksim.select_session(sessions, "q"))

    def test_session_labels_describe_trading_session_order(self):
        self.assertEqual(
            checksim.session_label(date(2026, 10, 9), 0, date(2026, 10, 9)),
            "Today",
        )
        self.assertEqual(
            checksim.session_label(date(2026, 10, 8), 1, date(2026, 10, 9)),
            "Previous trading session",
        )
        self.assertEqual(
            checksim.session_label(date(2026, 10, 6), 3, date(2026, 10, 9)),
            "3 trading sessions earlier",
        )

    def test_simulation_runs_only_after_successful_chk(self):
        with patch.object(
            checksim, "fetch_recent_index_history", return_value=object()
        ), patch.object(
            checksim,
            "_completed_session_dates",
            return_value=[
                date(2026, 10, 8),
                date(2026, 10, 9),
            ],
        ), patch.object(
            checksim, "input", return_value="1", create=True
        ), patch.object(checksim, "_run_stage", return_value=1) as run_stage:
            self.assertEqual(checksim.main(), 1)

        self.assertEqual(run_stage.call_count, 1)
        self.assertEqual(run_stage.call_args.args[0], "CHK test suite")

    def test_successful_chk_replays_the_selected_exact_session(self):
        with patch.object(
            checksim, "fetch_recent_index_history", return_value=object()
        ), patch.object(
            checksim,
            "_completed_session_dates",
            return_value=[
                date(2026, 10, 8),
                date(2026, 10, 9),
            ],
        ), patch.object(
            checksim, "input", return_value="2", create=True
        ), patch.object(checksim, "_run_stage", return_value=0) as run_stage:
            self.assertEqual(checksim.main(), 0)

        self.assertEqual(run_stage.call_count, 2)
        simulation = run_stage.call_args_list[1]
        self.assertEqual(simulation.args[0], "SIM replay for 2026-10-08")
        self.assertEqual(simulation.args[1][-2:], ["--session-date", "2026-10-08"])
