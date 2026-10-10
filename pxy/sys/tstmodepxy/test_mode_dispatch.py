import sys
import unittest
from contextlib import redirect_stdout
from datetime import date, datetime
from io import StringIO
from pathlib import Path
from unittest.mock import Mock, patch

import pandas as pd

SYS_DIR = Path(__file__).resolve().parents[1]
if str(SYS_DIR) not in sys.path:
    sys.path.insert(0, str(SYS_DIR))

import sysmodepxy
import sysexepxy
from tstmodepxy.backtest import (
    calculate_heikin_ashi,
    heikin_ashi_entry_exit_signals,
    print_book_table,
    run_backtest,
    scale_sim_lgt_calculator,
)


class ModeDispatchTests(unittest.TestCase):
    def test_book_report_prints_only_action_and_reason_columns(self):
        trade = {
            "tag": "WF0000001",
            "side": "CE",
            "entry_time": "2025-01-06 09:19:00",
            "exit_time": "2025-01-06 09:20:00",
            "entry_spot": 22000.0,
            "exit_spot": 22020.0,
            "index_points_per_unit": 20.0,
            "quantity": 1,
            "exit_reason": "production_exit",
        }
        output = StringIO()
        with redirect_stdout(output):
            print_book_table(
                1,
                trade,
                [{"GuiOrdId": "WF0000001"}],
                {
                    "entry_signal": "BUY",
                    "exit_signal": "BULL",
                    "pipe_output": "FRESH ENTRY",
                },
                "Target Hit & PnL Met",
            )

        lines = output.getvalue().strip().splitlines()
        self.assertEqual(lines[0], "| Action | Why action |")
        self.assertEqual(lines[1], "|---|---|")
        self.assertIn("Book 1: BUY CE", lines[2])
        self.assertIn("Fresh-entry BUY signal", lines[2])
        self.assertIn("Production target and minimum-P&L gates both passed", lines[2])
        self.assertTrue(all(line.count("|") == 3 for line in lines))

    def test_sim_scales_production_averaging_threshold_by_200(self):
        production_lgt = Mock(return_value=-22.5)
        sim_lgt = scale_sim_lgt_calculator(production_lgt)

        self.assertEqual(sim_lgt(0, 0, True, index_price=22500), -0.1125)
        production_lgt.assert_called_once_with(0, 0, True, index_price=22500)

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

    def test_backtest_selects_latest_requested_completed_sessions(self):
        import tstmodepxy.backtest as backtest

        dates = pd.date_range("2025-01-06 09:16", periods=4, freq="D")
        history = pd.DataFrame(
            {"Close": [100.0] * 4},
            index=dates,
        )
        with patch.object(
            backtest, "_completed_session_dates",
            return_value=[date(2025, 1, 6), date(2025, 1, 7), date(2025, 1, 8)],
        ):
            self.assertEqual(
                backtest.recent_sessions_with_records(history, 2),
                [date(2025, 1, 7), date(2025, 1, 8)],
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

    def test_heikin_ashi_entries_only_fire_on_color_switches(self):
        import tstmodepxy.backtest as backtest

        history = pd.DataFrame(
            {
                "Open": [10, 6, 12, 14, 12],
                "High": [10, 12, 14, 14, 12],
                "Low": [5, 6, 11, 4, 12],
                "Close": [6, 12, 14, 4, 12],
            }
        )
        ha = calculate_heikin_ashi(history)
        entries, exits = heikin_ashi_entry_exit_signals(ha)

        self.assertEqual(entries, ["SELL", "BUY", "NONE", "SELL", "BUY"])
        self.assertEqual(exits, ["BEAR", "BULL", "BULL", "BEAR", "BULL"])
        self.assertAlmostEqual(ha["Open"].iloc[1], 7.875)

    def test_heikin_ashi_doji_keeps_state_without_repeating_entry(self):
        from tstmodepxy.backtest import heikin_ashi_entry_exit_signals

        ha = pd.DataFrame(
            {"Open": [2, 1, 3], "Close": [1, 1, 4]}
        )
        entries, exits = heikin_ashi_entry_exit_signals(ha)
        self.assertEqual(entries, ["SELL", "NONE", "BUY"])
        self.assertEqual(exits, ["BEAR", "BEAR", "BULL"])

    def test_ha_signal_path_overrides_entry_exit_but_keeps_real_spot(self):
        import tstmodepxy.backtest as backtest

        timestamp = pd.date_range("2025-01-06 09:16", periods=2, freq="min")
        history = pd.DataFrame(
            {
                "Open": [10, 6],
                "High": [10, 12],
                "Low": [5, 6],
                "Close": [6, 12],
            },
            index=timestamp,
        )
        dashboard = Mock()
        dashboard.get_full_snapshot.return_value = {
            "entry": "NONE", "exit": "NONE"
        }
        with patch.object(
            backtest.importlib, "import_module", return_value=dashboard
        ), patch.object(
            backtest, "transform_market_data", side_effect=lambda frame: frame
        ):
            bars = backtest.calculate_strategy_signals(
                history, date(2025, 1, 6), heikin_ashi=True
            )

        self.assertEqual(
            [(bar["entry"], bar["exit"]) for bar in bars],
            [("SELL", "BEAR"), ("BUY", "BULL")],
        )
        self.assertEqual([bar["spot"] for bar in bars], [6.0, 12.0])
        self.assertEqual(bars[-1]["snapshot"]["entry"], "BUY")
        self.assertEqual(bars[-1]["snapshot"]["exit"], "BULL")

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
        self.assertGreaterEqual(ticker.history.call_count, 5)
        self.assertIn(
            "start",
            ticker.history.call_args_list[4].kwargs,
        )

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
                "within Yahoo's 28-day intraday-history window",
            ):
                backtest.fetch_recent_index_history()


if __name__ == "__main__":
    unittest.main()
