import sys
import unittest
from datetime import date, datetime
from pathlib import Path
from unittest.mock import Mock, patch

import pandas as pd

SYS_DIR = Path(__file__).resolve().parents[1]
if str(SYS_DIR) not in sys.path:
    sys.path.insert(0, str(SYS_DIR))

import sysmodepxy
import sysexepxy
from tstmodepxy.backtest import run_backtest


class ModeDispatchTests(unittest.TestCase):
    def test_prd_dispatch_uses_production_provider(self):
        with patch.object(sysmodepxy, "RUNMODE", "PRD"):
            result = sysmodepxy.dispatch_mode(
                "unused_provider", lambda: "production"
            )
        self.assertEqual(result, "production")

    def test_chk_dispatch_uses_mock_provider(self):
        with patch.object(sysmodepxy, "RUNMODE", "CHK"):
            result = sysmodepxy.dispatch_mode(
                "get_session", lambda: self.fail("PRD provider must not run")
            )
        self.assertIsNone(result)

    def test_sim_dispatch_fails_closed_in_production_engine_path(self):
        with patch.object(sysmodepxy, "RUNMODE", "SIM"):
            with self.assertRaisesRegex(RuntimeError, "syssimpxy.py --records 100"):
                sysmodepxy.dispatch_mode(
                    "unused_provider", lambda: self.fail("live provider must not run")
                )

    def test_nonproduction_start_messages_name_dedicated_commands(self):
        self.assertIn("syssimpxy.py --records 100", sysmodepxy.normal_start_message("SIM"))
        self.assertIn("unittest discover", sysmodepxy.normal_start_message("CHK"))

    def test_normal_supervisor_refuses_nonproduction_modes_with_instructions(self):
        for mode, command in (
            ("SIM", "syssimpxy.py --records 100"),
            ("CHK", "unittest discover"),
        ):
            with self.subTest(mode=mode), patch.object(
                sysexepxy, "RUNMODE", mode
            ), patch.object(
                sysexepxy, "dispatch_mode",
                side_effect=AssertionError("non-production mode must be rejected"),
            ), patch("builtins.print") as print_message:
                self.assertEqual(sysexepxy.start_loop(), 2)
                self.assertIn(
                    command,
                    print_message.call_args.args[0],
                )

    def test_walk_forward_requires_sim_before_fetching_market_data(self):
        import tstmodepxy.backtest as backtest

        with patch.object(backtest, "RUNMODE", "PRD"), patch.object(
            backtest, "fetch_recent_index_history",
            side_effect=AssertionError("history must not be fetched"),
        ):
            with self.assertRaisesRegex(RuntimeError, "requires RUNMODE='SIM'"):
                run_backtest()

    def test_sim_replay_does_not_gate_history_fetch_on_wall_clock(self):
        import tstmodepxy.backtest as backtest

        with patch.object(backtest, "RUNMODE", "SIM"), patch.object(
            backtest, "fetch_recent_index_history",
            side_effect=AssertionError("history must not be fetched"),
        ):
            with self.assertRaisesRegex(AssertionError, "history must not be fetched"):
                run_backtest()

    def test_backtest_chooses_latest_session_instead_of_a_random_one(self):
        import tstmodepxy.backtest as backtest

        history = pd.DataFrame(
            {"Close": [100.0, 101.0, 102.0]},
            index=pd.DatetimeIndex(
                [
                    datetime(2025, 1, 6, 9, 16),
                    datetime(2025, 1, 7, 15, 29),
                    datetime(2025, 1, 8, 15, 29),
                ]
            ),
        )
        self.assertEqual(
            backtest.latest_session_with_records(history),
            date(2025, 1, 8),
        )

    def test_strategy_signal_capture_redirects_dashboard_output(self):
        import tstmodepxy.backtest as backtest

        history = pd.DataFrame(
            {"Open": [100.0], "High": [101.0], "Low": [99.0], "Close": [100.5]},
            index=pd.DatetimeIndex([datetime(2025, 1, 6, 9, 16)]),
        )
        dashboard = Mock()
        dashboard.get_full_snapshot.return_value = {"entry": "NONE", "exit": "NONE"}
        dashboard.fetch_yf_data = Mock()
        with patch.object(backtest.importlib, "import_module", return_value=dashboard), patch.object(
            backtest, "transform_market_data", return_value=history
        ):
            bars = backtest.calculate_strategy_signals(history, date(2025, 1, 6))

        self.assertEqual(len(bars), 1)
        dashboard.get_full_snapshot.assert_called_once_with()

    def test_yahoo_history_columns_normalize_both_multiindex_orders(self):
        import tstmodepxy.backtest as backtest

        expected = ["Open", "High", "Low", "Close"]
        for columns in (
            pd.MultiIndex.from_product(
                [expected, ["^NSEI"]], names=["Price", "Ticker"]
            ),
            pd.MultiIndex.from_product(
                [["^NSEI"], expected], names=["Ticker", "Price"]
            ),
        ):
            with self.subTest(columns=columns.names):
                frame = pd.DataFrame([[1.0, 2.0, 0.5, 1.5]], columns=columns)
                normalized = backtest._normalize_history_columns(frame)
                self.assertEqual(list(normalized.columns), expected)
                self.assertIsInstance(normalized["Close"], pd.Series)

    def test_history_fetch_walks_back_until_a_complete_session_is_found(self):
        import tstmodepxy.backtest as backtest

        empty = pd.DataFrame(columns=["Open", "High", "Low", "Close"])
        old_session = pd.DataFrame(
            {
                "Open": [100.0, 101.0],
                "High": [101.0, 102.0],
                "Low": [99.0, 100.0],
                "Close": [100.5, 101.5],
            },
            index=pd.DatetimeIndex(
                [datetime(2025, 1, 6, 9, 15), datetime(2025, 1, 6, 15, 29)]
            ),
        )
        ticker = Mock()
        ticker.history.side_effect = [empty, empty, empty, empty, old_session]
        with patch.object(backtest.yf, "Ticker", return_value=ticker), patch.object(
            backtest, "_today_ist", return_value=date(2025, 1, 9)
        ):
            history = backtest.fetch_recent_index_history()

        self.assertEqual(history.index.date[-1], date(2025, 1, 6))
        self.assertEqual(ticker.history.call_count, 5)
        self.assertEqual(ticker.history.call_args_list[-1].kwargs["start"], "2025-01-06")

    def test_history_fetch_reports_when_no_complete_day_exists_in_window(self):
        import tstmodepxy.backtest as backtest

        ticker = Mock()
        ticker.history.return_value = pd.DataFrame(
            columns=["Open", "High", "Low", "Close"]
        )
        with patch.object(backtest.yf, "Ticker", return_value=ticker), patch.object(
            backtest, "_today_ist", return_value=date(2025, 1, 6)
        ):
            with self.assertRaisesRegex(
                RuntimeError,
                "within Yahoo's 7-day intraday-history window",
            ):
                backtest.fetch_recent_index_history()


if __name__ == "__main__":
    unittest.main()
