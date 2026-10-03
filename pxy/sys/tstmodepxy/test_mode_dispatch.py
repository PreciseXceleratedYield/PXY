import sys
import unittest
from datetime import date, datetime
from pathlib import Path
from unittest.mock import Mock, patch

import pandas as pd
from unittest.mock import patch

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
            with self.assertRaisesRegex(RuntimeError, "cannot dispatch engine providers"):
                sysmodepxy.dispatch_mode(
                    "unused_provider", lambda: self.fail("live provider must not run")
                )

    def test_normal_supervisor_routes_sim_to_replay_and_exits(self):
        with patch.object(sysexepxy, "RUNMODE", "SIM"), patch.object(
            sysexepxy, "dispatch_mode",
            side_effect=AssertionError("SIM must not enter engine dispatch"),
        ), patch("syssimpxy.main", return_value=0) as run_simulation:
            self.assertEqual(sysexepxy.start_loop(), 0)
        run_simulation.assert_called_once_with()

    def test_walk_forward_requires_sim_before_fetching_market_data(self):
        import tstmodepxy.backtest as backtest

        with patch.object(backtest, "RUNMODE", "PRD"), patch.object(
            backtest, "fetch_recent_index_history",
            side_effect=AssertionError("history must not be fetched"),
        ):
            with self.assertRaisesRegex(RuntimeError, "requires RUNMODE='SIM'"):
                run_backtest()

    def test_walk_forward_refuses_market_hours_before_fetching_data(self):
        import tstmodepxy.backtest as backtest

        with patch.object(backtest, "RUNMODE", "SIM"), patch.object(
            backtest, "is_actual_market_hours", return_value=True
        ), patch.object(
            backtest, "fetch_recent_index_history",
            side_effect=AssertionError("history must not be fetched"),
        ):
            with self.assertRaisesRegex(RuntimeError, "disabled during weekday market hours"):
                run_backtest()

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


if __name__ == "__main__":
    unittest.main()
