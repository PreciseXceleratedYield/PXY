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
    SimBookCycle,
    choose_replay_session,
    print_book_table,
    print_report,
    run_backtest,
    scale_sim_lgt_calculator,
)


class ModeDispatchTests(unittest.TestCase):
    def test_sim_final_report_ends_with_total_spot_points_gained(self):
        output = StringIO()
        with redirect_stdout(output):
            print_report(
                pd.DataFrame(),
                [date(2025, 1, 10)],
                [{"points": 15.7, "exit_reason": "production_exit"}],
                [],
                "trades.csv",
                "decisions.csv",
                "orders.csv",
                "runtime.log",
            )

        self.assertEqual(
            output.getvalue().strip().splitlines()[-1],
            "TOTAL SPOT POINTS GAINED: +15.70",
        )

    def test_sim_multi_day_report_shows_separate_daily_points(self):
        output = StringIO()
        with redirect_stdout(output):
            print_report(
                pd.DataFrame(),
                [date(2025, 1, 9), date(2025, 1, 10)],
                [
                    {"session": "2025-01-09", "points": 12.5, "exit_reason": "production_exit"},
                    {"session": "2025-01-10", "points": -2.0, "exit_reason": "production_exit"},
                ],
                [],
                "trades.csv",
                "decisions.csv",
                "orders.csv",
                "runtime.log",
            )

        lines = output.getvalue().splitlines()
        self.assertIn("| Session date | Daily points |", lines)
        self.assertIn("| 2025-01-09 | +12.50 |", lines)
        self.assertIn("| 2025-01-10 | -2.00 |", lines)
        self.assertFalse(any("Cumulative" in line for line in lines))
        self.assertFalse(any("TOTAL SPOT POINTS GAINED" in line for line in lines))

    def test_interactive_sim_menu_runs_the_selected_date(self):
        import tstmodepxy.backtest as backtest

        dates = pd.bdate_range("2025-01-06", periods=6)
        index = pd.DatetimeIndex(
            [pd.Timestamp(day).replace(hour=15, minute=29) for day in dates]
        )
        history = pd.DataFrame(
            {
                "Open": [1.0] * len(index),
                "High": [1.0] * len(index),
                "Low": [1.0] * len(index),
                "Close": [1.0] * len(index),
            },
            index=index,
        )
        with (
            patch.object(backtest, "get_nse_fo_holidays", return_value=frozenset()),
            patch.object(backtest, "fetch_recent_index_history", return_value=history),
            patch.object(backtest.sys, "stdin", Mock(isatty=Mock(return_value=True))),
            patch("builtins.input", side_effect=["2", "2"]),
            patch.object(backtest, "run_backtest") as replay,
            redirect_stdout(StringIO()),
        ):
            self.assertEqual(backtest.main([]), 0)

        self.assertEqual(replay.call_args.kwargs["session_date"], date(2025, 1, 10))
        self.assertIs(replay.call_args.kwargs["history"], history)
        self.assertFalse(replay.call_args.kwargs["book_by_book"])

    def test_interactive_sim_menu_can_select_latest_seven_sessions(self):
        import tstmodepxy.backtest as backtest

        dates = pd.bdate_range("2025-01-06", periods=9)
        index = pd.DatetimeIndex(
            [pd.Timestamp(day).replace(hour=15, minute=29) for day in dates]
        )
        history = pd.DataFrame(
            {
                "Open": [1.0] * len(index),
                "High": [1.0] * len(index),
                "Low": [1.0] * len(index),
                "Close": [1.0] * len(index),
            },
            index=index,
        )
        with (
            patch.object(backtest, "get_nse_fo_holidays", return_value=frozenset()),
            patch.object(backtest, "fetch_recent_index_history", return_value=history),
            patch.object(backtest.sys, "stdin", Mock(isatty=Mock(return_value=True))),
            patch("builtins.input", side_effect=["6", "2"]),
            patch.object(backtest, "run_backtest") as replay,
            redirect_stdout(StringIO()) as output,
        ):
            self.assertEqual(backtest.main([]), 0)

        self.assertIsNone(replay.call_args.kwargs["session_date"])
        self.assertEqual(replay.call_args.kwargs["session_count"], 7)
        self.assertIs(replay.call_args.kwargs["history"], history)
        self.assertIn("Run the latest 7 available", output.getvalue())

    def test_interactive_sim_can_choose_pause_between_books(self):
        import tstmodepxy.backtest as backtest

        with (
            patch.object(backtest, "RUNMODE", "SIM"),
            patch.object(backtest.sys, "stdin", Mock(isatty=Mock(return_value=True))),
            patch("builtins.input", return_value="1"),
            patch.object(backtest, "run_backtest") as replay,
            redirect_stdout(StringIO()),
        ):
            self.assertEqual(backtest.main(["--session-date", "2025-01-10"]), 0)

        self.assertTrue(replay.call_args.kwargs["book_by_book"])

    def test_all_books_flag_skips_replay_style_prompt(self):
        import tstmodepxy.backtest as backtest

        with (
            patch.object(backtest, "RUNMODE", "SIM"),
            patch.object(backtest.sys, "stdin", Mock(isatty=Mock(return_value=True))),
            patch("builtins.input", side_effect=AssertionError("unexpected prompt")),
            patch.object(backtest, "run_backtest") as replay,
            redirect_stdout(StringIO()),
        ):
            self.assertEqual(
                backtest.main(["--session-date", "2025-01-10", "--all-books"]),
                0,
            )

        self.assertFalse(replay.call_args.kwargs["book_by_book"])

    def test_sim_session_menu_selection_uses_newest_completed_dates(self):
        import tstmodepxy.backtest as backtest

        index = pd.DatetimeIndex(
            [
                "2025-01-06 15:29",
                "2025-01-07 15:29",
                "2025-01-08 15:29",
                "2025-01-09 15:29",
                "2025-01-10 15:29",
            ]
        )
        history = pd.DataFrame({"Close": [1] * len(index)}, index=index)

        with patch.object(backtest, "get_nse_fo_holidays", return_value=frozenset()):
            self.assertEqual(
                choose_replay_session(history, "1"),
                date(2025, 1, 10),
            )
            self.assertEqual(
                choose_replay_session(history, "5"),
                date(2025, 1, 6),
            )
            self.assertIsNone(choose_replay_session(history, "q"))
            self.assertIsNone(choose_replay_session(history, "6"))

    def test_sim_book_is_reportable_only_after_whole_portfolio_returns_flat(self):
        book = SimBookCycle()
        pe_trade = {"side": "PE"}
        ce_trade = {"side": "CE"}

        self.assertIsNone(book.record_tick("0CE0PE", "0CE1PE", [], True))
        self.assertIsNone(book.record_tick("0CE1PE", "1CE1PE", [], True))
        self.assertIsNone(book.record_tick("1CE1PE", "1CE0PE", [pe_trade], False))

        completed = book.record_tick("1CE0PE", "0CE0PE", [ce_trade], False)
        self.assertEqual(completed, [pe_trade, ce_trade])
        self.assertIsNone(book.record_tick("0CE0PE", "0CE0PE", [], False))

    def test_book_report_prints_flat_to_flat_chronological_ist_journal(self):
        trade = {
            "tag": "WF0000001",
            "side": "PE",
            "entry_time": "2025-01-06 09:19:00",
            "exit_time": "2025-01-06 09:32:00",
            "entry_spot": 22702.70,
            "exit_spot": 22698.75,
            "index_points_per_unit": 3.95,
            "quantity": 1,
            "exit_reason": "production_exit",
        }
        counter_leg = {
            **trade,
            "tag": "WF0000002",
            "side": "CE",
            "entry_time": "2025-01-06 09:20:00",
            "exit_time": "2025-01-06 09:27:00",
            "entry_spot": 22720.35,
            "exit_spot": 22732.10,
            "index_points_per_unit": 11.75,
        }
        fresh_entry = {
            "entry_signal": "SELL",
            "exit_signal": "BEAR",
            "pipe_output": "FRESH ENTRY",
        }
        counter_entry = {
            "entry_signal": "NONE",
            "exit_signal": "BULL",
            "pipe_output": "COUNTER-BUY",
        }
        output = StringIO()
        with redirect_stdout(output):
            print_book_table(
                1,
                [
                    (trade, [{"GuiOrdId": "WF0000001"}], fresh_entry, "Target Hit & PnL Met"),
                    (counter_leg, [{"GuiOrdId": "WF0000002"}], counter_entry, "Target Hit & PnL Met"),
                ],
            )

        lines = output.getvalue().strip().splitlines()
        self.assertEqual(lines[0], "Book 1 — flat-to-flat cycle")
        self.assertEqual(lines[1], "| Time (IST) | Journal | Why action |")
        self.assertEqual(lines[2], "|---|---|---|")
        self.assertIn(
            "| 09:19:00 | FRESH ENTRY (SELL): Started Book 1 with BUY PE",
            lines[3],
        )
        self.assertIn("| 09:20:00 | COUNTER (BULL): BUY CE", lines[4])
        self.assertIn("| 09:27:00 | TARGET: SELL CE", lines[5])
        self.assertIn("Counter-leg followed the BULL signal.", lines[4])
        self.assertIn("Production target and minimum-P&L gates both passed", lines[5])
        self.assertIn("| 09:32:00 | TARGET: SELL PE", lines[6])
        self.assertIn("book flat", lines[6])
        self.assertIn("Fresh entry accepted while the portfolio was flat.", lines[3])
        self.assertIn("Book 1 total: +15.70 pts", lines[7])
        self.assertTrue(all(line.count("|") == 4 for line in lines[2:]))

    def test_sim_journal_classifies_avg_risk_and_peakdip_signals(self):
        from tstmodepxy.backtest import _book_entry_signal, _book_exit_signal

        self.assertEqual(
            _book_entry_signal([], {
                "entry_signal": "NONE",
                "exit_signal": "BEAR",
                "pipe_output": "PE Averaged successfully",
            }),
            ("AVG", "BEAR"),
        )
        self.assertEqual(
            _book_exit_signal(
                {
                    "exit_time": "2025-01-06 10:00:00",
                    "exit_reason": "risk_bar",
                },
                {"exit_signal": "BULL"},
                "",
            )[0],
            "RISK",
        )
        self.assertEqual(
            _book_exit_signal(
                {
                    "exit_time": "2025-01-06 10:00:00",
                    "exit_reason": "production_exit",
                },
                {"exit_signal": "BEAR"},
                "Deep reversal: BUY with PE11 past depth",
            )[0],
            "PEAKDIP",
        )

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

    def test_strategy_signals_apply_new_book_cutoff_at_each_historical_candle(self):
        import tstmodepxy.backtest as backtest

        history = pd.DataFrame(
            {
                "Open": [100.0, 100.0],
                "High": [101.0, 101.0],
                "Low": [99.0, 99.0],
                "Close": [100.5, 100.5],
            },
            index=pd.DatetimeIndex(
                [datetime(2025, 1, 6, 13, 59), datetime(2025, 1, 6, 14, 0)]
            ),
        )
        dashboard = Mock()

        def historical_snapshot():
            entry, exit_signal = dashboard.get_entry_signal(history)
            return {"entry": entry, "exit": exit_signal}

        dashboard.get_full_snapshot.side_effect = historical_snapshot
        with (
            patch.object(backtest.importlib, "import_module", return_value=dashboard),
            patch.object(backtest, "transform_market_data", return_value=history),
            patch.object(backtest.sysentrpxy, "SYSENTRPXY_VARIANT", "MKT"),
            patch.object(backtest.sysentrpxy, "get_market_signal", return_value="BULL"),
            patch.object(
                backtest.sysentrpxy,
                "get_signal_depth_analysis",
                return_value={"past_depth": "PE3", "ce_depth": 1, "pe_depth": 1},
            ),
        ):
            bars = backtest.calculate_strategy_signals(history, date(2025, 1, 6))

        self.assertEqual([bar["entry"] for bar in bars], ["BUY", "NONE"])
        self.assertEqual([bar["exit"] for bar in bars], ["BULL", "BULL"])

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
