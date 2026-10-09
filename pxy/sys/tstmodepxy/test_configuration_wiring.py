import re
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import date, time, timedelta
from io import StringIO
from pathlib import Path
from unittest.mock import mock_open, patch

import pandas as pd

SYS_DIR = Path(__file__).resolve().parents[1]
EXE_DIR = SYS_DIR / "exe"
RUN_DIR = EXE_DIR / "run"
if str(SYS_DIR) not in sys.path:
    sys.path.insert(0, str(SYS_DIR))
if str(EXE_DIR) not in sys.path:
    sys.path.insert(0, str(EXE_DIR))
if str(RUN_DIR) not in sys.path:
    sys.path.insert(0, str(RUN_DIR))

import exeltgtpxy
import exeotmpxy
import exeacgpxy
import execbuypxy
import exeexitpxy
import exeforcepxy
import exeavxpxy
import exeentrpxy
import sysdashpxy
import sysentrpxy
import sysmktpxy
import sysdptpxy
import sysdthapxy
import syspxy
import sysstrndpxy
import runniftypxy
from syscnfgpxy import (
    SYSCNFGPXY_ACTION_COOLDOWN_SECONDS,
    SYSCNFGPXY_EXCHANGE_OPEN,
    SYSCNFGPXY_PREOPEN_START,
    SYSCNFGPXY_MARKET_OPEN,
    SYSCNFGPXY_ENGINE_CLOSE,
    SYSCNFGPXY_TRADING_PIPE_CLOSE,
    SYSCNFGPXY_TRADING_DAY_END,
    SYSCNFGPXY_AVERAGING_START,
    SYSCNFGPXY_ENTRY_CUTOFF,
    SYSCNFGPXY_SQUAREOFF_START,
    SYSCNFGPXY_SQUAREOFF_ALL_START,
    SYSCNFGPXY_SQUAREOFF_END,
    SYSCNFGPXY_TIMEZONE,
    SYSSTRNDPXY_ST1_ATR_VALUE,
    SYSSTRNDPXY_ST1_FACTOR,
    SYSDTAFPXY_FIXED_BRICK_SIZE,
    SYSSMAPXY_VARIANT,
    SYSSTRNDPXY_CHART_TARGET_ROWS,
    EXEAMSPXY_MAX_INVESTMENT,
)
from sysdtafpxy import apply_ohlc_transformation
from syssmapxy import calculate_moving_average, get_sma
from sysdecisionpxy import (
    averaging_trigger_sides,
    counter_leg_script,
    entry_order_command,
    entry_signal_valid,
)
import syskatrpxy
from systrcalpxy import _compute_single_st


class ConfigurationWiringTests(unittest.TestCase):
    def setUp(self):
        self.cooldown_patch = patch.object(sysentrpxy, "cooldown_remaining", return_value=0)
        self.cooldown_patch.start()

    def tearDown(self):
        self.cooldown_patch.stop()

    def test_market_hour_aliases_share_the_canonical_schedule(self):
        import syscnfgpxy

        self.assertEqual(syscnfgpxy.SYSEXEPXY_MARKET_OPEN, SYSCNFGPXY_MARKET_OPEN)
        self.assertEqual(syscnfgpxy.SYSEXEPXY_MARKET_CLOSE, SYSCNFGPXY_ENGINE_CLOSE)
        self.assertEqual(syscnfgpxy.EXEPXYPXY_MARKET_OPEN, SYSCNFGPXY_MARKET_OPEN)
        self.assertEqual(
            syscnfgpxy.EXEPXYPXY_MARKET_CLOSE, SYSCNFGPXY_TRADING_PIPE_CLOSE
        )
        self.assertEqual(syscnfgpxy.EXEENTRPXY_PREOPEN_START, SYSCNFGPXY_PREOPEN_START)
        self.assertEqual(syscnfgpxy.EXEENTRPXY_PREOPEN_END, SYSCNFGPXY_MARKET_OPEN)
        self.assertEqual(syscnfgpxy.EXEENTRPXY_ENTRY_CUTOFF, SYSCNFGPXY_ENTRY_CUTOFF)
        self.assertEqual(syscnfgpxy.EXEENTRPXY_SQUAREOFF_END, SYSCNFGPXY_SQUAREOFF_END)
        self.assertEqual(syscnfgpxy.EXEAVXPXY_MARKET_START, SYSCNFGPXY_AVERAGING_START)
        self.assertEqual(syscnfgpxy.EXEAVXPXY_MARKET_END, SYSCNFGPXY_ENTRY_CUTOFF)
        self.assertEqual(syscnfgpxy.EXECBUYPXY_CUTOFF, SYSCNFGPXY_ENTRY_CUTOFF)
        self.assertEqual(syscnfgpxy.EXEEXITPXY_SQOFF_START, SYSCNFGPXY_SQUAREOFF_START)
        self.assertEqual(
            syscnfgpxy.EXEEXITPXY_SQOFF_ALL_START, SYSCNFGPXY_SQUAREOFF_ALL_START
        )
        self.assertEqual(syscnfgpxy.EXEEXITPXY_SQOFF_END, SYSCNFGPXY_SQUAREOFF_END)
        self.assertEqual(
            syscnfgpxy.TSTPOINTBTPXY_TRADING_DAY_START, SYSCNFGPXY_EXCHANGE_OPEN
        )
        self.assertEqual(
            syscnfgpxy.TSTPOINTBTPXY_TRADING_DAY_END, SYSCNFGPXY_TRADING_DAY_END
        )
        self.assertEqual(syscnfgpxy.TSTPOINTBTPXY_MARKET_OPEN, SYSCNFGPXY_MARKET_OPEN)
        self.assertEqual(
            syscnfgpxy.TSTPOINTBTPXY_MARKET_CLOSE, SYSCNFGPXY_TRADING_PIPE_CLOSE
        )
        self.assertEqual(
            syscnfgpxy.TSTPOINTBTPXY_FORCE_EXIT_TIME, SYSCNFGPXY_SQUAREOFF_ALL_START
        )

    def test_supertrend_variants_use_fixed_atr_value_five(self):
        index = pd.date_range("2026-10-07", periods=3, freq="min")
        frame = pd.DataFrame(
            {
                "Open": [99.0, 100.0, 101.0],
                "High": [101.0, 102.0, 103.0],
                "Low": [98.0, 99.0, 100.0],
                "Close": [100.0, 101.0, 102.0],
            },
            index=index,
        )
        atr = SYSSTRNDPXY_ST1_ATR_VALUE
        factor = SYSSTRNDPXY_ST1_FACTOR
        self.assertEqual(atr, 5.0)
        self.assertEqual(factor, 1.4)

        single_line, _, _, _ = _compute_single_st(frame, factor=factor, atr_value=atr)
        first_hl2 = (frame["High"].iloc[0] + frame["Low"].iloc[0]) / 2
        self.assertEqual(single_line.iloc[0], first_hl2 + factor * atr)

    def test_syspxy_snapshot_passes_through_sma_status(self):
        snapshot_df = pd.DataFrame({"Close": [100.0]})
        chart_df = pd.DataFrame({"Close": [100.0] * SYSSTRNDPXY_CHART_TARGET_ROWS})
        with (
            patch.object(syspxy, "dispatch_mode", return_value=None),
            patch.object(syspxy, "export_supertrend_json") as export_chart,
            patch.object(
                syspxy,
                "get_full_snapshot",
                return_value={
                    "sma": "BEAR",
                    "df": snapshot_df,
                    "chart_df": chart_df,
                },
            ),
            patch.object(syspxy.os, "makedirs"),
            patch("builtins.open", mock_open()),
        ):
            self.assertEqual(syspxy.get_all_data()["sma"], "BEAR")
        export_chart.assert_called_once_with(chart_df)

    def test_supertrend_chart_json_includes_rolling_sma50(self):
        index = pd.date_range("2026-10-07", periods=52, freq="min")
        closes = [float(value) for value in range(1, 53)]
        frame = pd.DataFrame(
            {
                "Open": closes,
                "High": [value + 1 for value in closes],
                "Low": [value - 1 for value in closes],
                "Close": closes,
            },
            index=index,
        )
        with tempfile.TemporaryDirectory(prefix="pxy-sma-chart-") as temp:
            output_file = Path(temp) / "webchrtpxy.json"
            exported = sysstrndpxy.export_supertrend_json(
                sysstrndpxy.calculate_supertrend(frame), str(output_file)
            )
            self.assertTrue(output_file.exists())

        self.assertIsNone(exported[0]["sma50"])
        self.assertEqual(exported[-1]["sma50"], 27.5)
        self.assertEqual(exported[-1]["tsma50"], 52.0)

    def test_chart_ma_series_are_full_across_the_visible_60_bars(self):
        closes = [
            float(value)
            for value in range(1, SYSSTRNDPXY_CHART_TARGET_ROWS + 1)
        ]
        frame = pd.DataFrame(
            {
                "Open": closes,
                "High": [value + 1 for value in closes],
                "Low": [value - 1 for value in closes],
                "Close": closes,
            },
            index=pd.date_range(
                "2026-10-07", periods=SYSSTRNDPXY_CHART_TARGET_ROWS, freq="min"
            ),
        )

        processed = sysstrndpxy.calculate_supertrend(frame)

        self.assertEqual(processed["sma_50"].tail(60).notna().sum(), 60)
        self.assertEqual(processed["tsma_50"].tail(60).notna().sum(), 60)

    def test_chart_history_covers_the_visible_50_period_average_window(self):
        index = pd.date_range(
            "2026-10-07", periods=SYSSTRNDPXY_CHART_TARGET_ROWS, freq="min"
        )
        closes = [
            float(value)
            for value in range(1, SYSSTRNDPXY_CHART_TARGET_ROWS + 1)
        ]
        frame = pd.DataFrame(
            {
                "Open": closes,
                "High": [value + 1 for value in closes],
                "Low": [value - 1 for value in closes],
                "Close": closes,
            },
            index=index,
        )

        def add_trend_columns(source):
            output = source.copy()
            output["st_line"] = output["Close"]
            output["st_mirror"] = output["Close"]
            output["ST_Trend"] = "BULL"
            output["ST"] = output["Close"]
            return output

        with (
            patch.object(sysdashpxy, "fetch_yf_data", return_value=frame) as fetch,
            patch.object(sysdashpxy, "get_candle_visual", return_value=""),
            patch.object(
                sysdashpxy,
                "get_pxy_data",
                return_value=(0, 0, "", frame),
            ),
            patch.object(
                sysdashpxy,
                "detect_pxy_flip_signal",
                return_value=("BULL", 0, 0, 0),
            ),
            patch.object(sysdashpxy, "calculate_adx", return_value=(1.0, 1.0)),
            patch.object(sysdashpxy, "calculate_atr", return_value=pd.Series([1.0])),
            patch.object(sysdashpxy, "calculate_dynamic_k", return_value=1),
            patch.object(sysdashpxy, "detect_raw_direction", return_value=(110, "UP")),
            patch.object(
                sysdashpxy,
                "calculate_supertrend",
                side_effect=add_trend_columns,
            ),
            patch.object(sysdashpxy, "get_ce_pe_power", return_value=(1, 1, 1)),
            patch.object(sysdashpxy, "get_entry_signal", return_value=("BUY", "BULL")),
            patch.object(sysdashpxy, "get_day_candle_bar", return_value=""),
            patch.object(sysdashpxy, "get_bos_bar", return_value=("NONE", None)),
            patch.object(
                sysdashpxy,
                "get_sma",
                return_value={"status": "BULL"},
            ),
        ):
            snapshot = sysdashpxy.get_full_snapshot()

        fetch.assert_called_once_with(target_rows=SYSSTRNDPXY_CHART_TARGET_ROWS)
        self.assertEqual(len(snapshot["df"]), 60)
        self.assertEqual(len(snapshot["chart_df"]), SYSSTRNDPXY_CHART_TARGET_ROWS)

    def test_sysmapxy_defaults_to_tsma_and_keeps_sma_selectable(self):
        closes = pd.Series([float(value) for value in range(1, 61)])

        self.assertEqual(SYSSMAPXY_VARIANT, "TSMA")
        self.assertEqual(
            __import__("pxyconfigwebpxy").ENUMS["SYSSMAPXY_VARIANT"],
            ("SMA", "TSMA"),
        )
        self.assertEqual(
            calculate_moving_average(closes, period=50, variant="TSMA").iloc[-1],
            60.0,
        )
        self.assertEqual(
            calculate_moving_average(closes, period=50, variant="SMA").iloc[-1],
            35.5,
        )
        self.assertEqual(get_sma(pd.DataFrame({"Close": closes}))["variant"], "TSMA")
        self.assertEqual(
            get_sma(pd.DataFrame({"Close": closes}), variant="SMA")["value"],
            35.5,
        )

    def test_sma_status_is_relative_to_50_period_simple_moving_average(self):
        above = pd.DataFrame({"Close": [100.0] * 49 + [101.0]})
        below = pd.DataFrame({"Close": [100.0] * 49 + [99.0]})

        self.assertEqual(get_sma(above, period=50, variant="SMA")["status"], "BULL")
        self.assertEqual(get_sma(below, period=50, variant="SMA")["status"], "BEAR")

    def test_entry_and_exit_follow_directional_supertrend(self):
        frame = pd.DataFrame({"Close": [1]})
        with (
            patch.object(sysentrpxy, "SYSENTRPXY_SIGNAL_MODE", "STS"),
            patch.object(sysentrpxy, "detect_raw_direction") as direction,
            patch.object(sysentrpxy, "get_market_signal") as market,
            patch.object(
                sysentrpxy,
                "calculate_supertrend",
                return_value=pd.DataFrame({"ST_Trend": ["BULL"]}),
            ),
        ):
            self.assertEqual(
                sysentrpxy.get_entry_signal(frame, current_time=time(9, 30)),
                ("BUY", "BULL"),
            )
        direction.assert_not_called()
        market.assert_not_called()

    def test_bear_supertrend_returns_sell_and_bear_even_when_market_is_bull(self):
        frame = pd.DataFrame({"Close": [1]})
        with (
            patch.object(sysentrpxy, "SYSENTRPXY_SIGNAL_MODE", "STS"),
            patch.object(sysentrpxy, "detect_raw_direction") as direction,
            patch.object(sysentrpxy, "get_market_signal") as market,
            patch.object(
                sysentrpxy,
                "calculate_supertrend",
                return_value=pd.DataFrame({"ST_Trend": ["BEAR"]}),
            ),
        ):
            self.assertEqual(
                sysentrpxy.get_entry_signal(frame, current_time=time(9, 31)),
                ("SELL", "BEAR"),
            )
        direction.assert_not_called()
        market.assert_not_called()

    def test_side_supertrend_keeps_side_entry_and_uses_market_exit(self):
        frame = pd.DataFrame({"Close": [1]})
        with (
            patch.object(sysentrpxy, "SYSENTRPXY_SIGNAL_MODE", "STS"),
            patch.object(sysentrpxy, "get_market_signal", return_value=("NONE", "BEAR")),
            patch.object(
                sysentrpxy,
                "calculate_supertrend",
                return_value=pd.DataFrame({"ST_Trend": ["SIDE"]}),
            ),
        ):
            self.assertEqual(
                sysentrpxy.get_entry_signal(frame, current_time=time(9, 31)),
                ("SIDE", "BEAR"),
            )

    def test_side_supertrend_never_returns_side_exit_without_market_direction(self):
        frame = pd.DataFrame({"Close": [1]})
        with (
            patch.object(sysentrpxy, "SYSENTRPXY_SIGNAL_MODE", "STS"),
            patch.object(sysentrpxy, "get_market_signal", return_value=("NONE", "NONE")),
            patch.object(
                sysentrpxy,
                "calculate_supertrend",
                return_value=pd.DataFrame({"ST_Trend": ["SIDE"]}),
            ),
        ):
            self.assertEqual(
                sysentrpxy.get_entry_signal(frame, current_time=time(9, 31)),
                ("SIDE", "NONE"),
            )

    def test_market_direction_is_used_only_before_0930(self):
        frame = pd.DataFrame({"Close": [1]})
        with (
            patch.object(sysentrpxy, "SYSENTRPXY_SIGNAL_MODE", "STS"),
            patch.object(
                sysentrpxy, "detect_raw_direction", return_value=(1, "UP")
            ) as direction,
            patch.object(sysentrpxy, "calculate_supertrend") as supertrend,
        ):
            self.assertEqual(
                sysentrpxy.get_entry_signal(frame, current_time=time(9, 29, 59)),
                ("BUY", "BULL"),
            )
        direction.assert_called_once_with(frame)
        supertrend.assert_not_called()

    def test_morning_window_uses_direction_for_entry_and_exit_without_supertrend(self):
        frame = pd.DataFrame({"Close": [1]})
        for current_time, direction, expected in (
            (time(9, 0), "UP", ("BUY", "BULL")),
            (time(9, 29, 59), "DOWN", ("SELL", "BEAR")),
            (time(9, 29), "NONE", ("NONE", "NONE")),
        ):
            with (
                self.subTest(current_time=current_time),
                patch.object(
                    sysentrpxy,
                    "SYSENTRPXY_SIGNAL_MODE",
                    "STS",
                ),
                patch.object(
                    sysentrpxy,
                    "detect_raw_direction",
                    return_value=(1, direction),
                ),
                patch.object(sysentrpxy, "calculate_supertrend") as supertrend,
            ):
                self.assertEqual(
                    sysentrpxy.get_entry_signal(frame, current_time=current_time),
                    expected,
                )
                supertrend.assert_not_called()

    def test_mkt_mode_routes_through_market_signal_all_session(self):
        frame = pd.DataFrame({"Close": [1]})
        with (
            patch.object(sysentrpxy, "SYSENTRPXY_SIGNAL_MODE", "MKT"),
            patch.object(
                sysentrpxy, "get_market_signal", return_value=("SELL", "BEAR")
            ) as market,
            patch.object(sysentrpxy, "calculate_supertrend") as supertrend,
        ):
            self.assertEqual(
                sysentrpxy.get_entry_signal(frame, current_time=time(12, 0)),
                ("SELL", "BEAR"),
            )
        market.assert_called_once_with(frame)
        supertrend.assert_not_called()

    def test_market_signal_uses_three_close_v_shapes(self):
        with patch.object(sysmktpxy, "SYSMKTPXY_DEBUG_ENABLED", False):
            self.assertEqual(
                sysmktpxy.get_signal(pd.DataFrame({"Close": [10.0, 8.0, 9.0]})),
                ("BUY", "BULL"),
            )
            self.assertEqual(
                sysmktpxy.get_signal(pd.DataFrame({"Close": [8.0, 10.0, 9.0]})),
                ("SELL", "BEAR"),
            )
            self.assertEqual(
                sysmktpxy.get_signal(pd.DataFrame({"Close": [8.0, 9.0, 10.0]})),
                ("NONE", "BULL"),
            )
            self.assertEqual(
                sysmktpxy.get_signal(pd.DataFrame({"Close": [10.0, 9.0, 8.0]})),
                ("NONE", "BEAR"),
            )
            for closes in ([8.0, 9.0, 9.0], [9.0, 9.0, 10.0], [9.0, 9.0, 9.0]):
                with self.subTest(closes=closes):
                    self.assertEqual(
                        sysmktpxy.get_signal(pd.DataFrame({"Close": closes})),
                        ("NONE", "NONE"),
                    )

    def test_market_signal_requires_three_closes(self):
        with patch.object(sysmktpxy, "SYSMKTPXY_DEBUG_ENABLED", False):
            self.assertEqual(
                sysmktpxy.get_signal(pd.DataFrame({"Close": [10.0, 8.0]})),
                ("NONE", "NONE"),
            )

    def test_market_signal_can_exclude_running_candle(self):
        frame = pd.DataFrame({"Close": [10.0, 8.0, 9.0, 7.0]})
        with (
            patch.object(sysmktpxy, "SYSMKTPXY_DEBUG_ENABLED", False),
            patch.object(sysdthapxy, "SYSDTHAPXY_INCLUDE_RUNNING_CANDLE", "YES"),
        ):
            self.assertEqual(sysmktpxy.get_signal(frame), ("SELL", "BEAR"))
        with (
            patch.object(sysmktpxy, "SYSMKTPXY_DEBUG_ENABLED", False),
            patch.object(sysdthapxy, "SYSDTHAPXY_INCLUDE_RUNNING_CANDLE", "NO"),
        ):
            self.assertEqual(sysmktpxy.get_signal(frame), ("BUY", "BULL"))
            self.assertEqual(
                sysmktpxy.get_signal(frame.iloc[:3]),
                ("NONE", "NONE"),
            )

    def test_market_signal_delegates_to_dtha_analysis(self):
        frame = pd.DataFrame({"Close": [10.0, 8.0, 9.0]})
        with (
            patch.object(sysmktpxy, "SYSMKTPXY_DEBUG_ENABLED", False),
            patch.object(
                sysmktpxy,
                "get_signal_depth_analysis",
                wraps=sysdthapxy.get_signal_depth_analysis,
            ) as analysis,
        ):
            self.assertEqual(sysmktpxy.get_signal(frame), ("BUY", "BULL"))
        analysis.assert_called_once_with(frame)

    def test_dtha_returns_one_pattern_signal_and_mkt_splits_it(self):
        expected_signals = {
            (10.0, 8.0, 9.0): ("BUY", ("BUY", "BULL")),
            (8.0, 10.0, 9.0): ("SELL", ("SELL", "BEAR")),
            (8.0, 9.0, 10.0): ("BULL", ("NONE", "BULL")),
            (10.0, 9.0, 8.0): ("BEAR", ("NONE", "BEAR")),
            (8.0, 9.0, 9.0): ("NONE", ("NONE", "NONE")),
        }
        with patch.object(sysmktpxy, "SYSMKTPXY_DEBUG_ENABLED", False):
            for closes, (expected_signal, expected_pair) in expected_signals.items():
                with self.subTest(closes=closes):
                    analysis = sysdthapxy.get_signal_depth_analysis(
                        pd.DataFrame({"Close": closes})
                    )
                    self.assertEqual(analysis["signal"], expected_signal)
                    self.assertNotIn("entry", analysis)
                    self.assertNotIn("exit", analysis)
                    self.assertEqual(
                        sysmktpxy.get_signal(pd.DataFrame({"Close": closes})),
                        expected_pair,
                    )

    def test_dtha_exposes_direction_and_marks_flat_bars_neutrally(self):
        frame = pd.DataFrame(
            {
                "Open": [9.0, 9.0, 9.0, 9.0],
                "High": [11.0, 11.0, 11.0, 11.0],
                "Low": [8.0, 8.0, 8.0, 8.0],
                "Close": [10.0, 9.0, 9.0, 10.0],
            }
        )
        _, _, colors, output = sysdthapxy.get_pxy_data(df=frame)
        self.assertEqual(
            sysdthapxy.get_close_direction_series(frame["Close"]).tolist(),
            ["UNKNOWN", "DOWN", "FLAT", "UP"],
        )
        self.assertEqual(colors.tolist(), ["green", "red", "flat", "green"])
        self.assertEqual(
            output["pxy_direction"].tolist(),
            ["UNKNOWN", "DOWN", "FLAT", "UP"],
        )

    def test_depth_keeps_growing_after_configured_lookback(self):
        closes = [float(value) for value in range(100, 126)]
        frame = pd.DataFrame(
            {
                "Open": [value - 1 for value in closes],
                "High": [value + 1 for value in closes],
                "Low": [value - 2 for value in closes],
                "Close": closes,
            }
        )
        _, _, ce_depth, pe_depth = sysdptpxy.detect_pxy_flip_signal(df=frame)
        self.assertEqual(ce_depth, len(closes) - 1)
        self.assertEqual(pe_depth, 1)

    def test_market_signal_and_depth_share_flat_and_running_candle_rules(self):
        frame = pd.DataFrame(
            {
                "Open": [10.0, 9.0, 9.0, 9.0],
                "High": [11.0, 10.0, 10.0, 10.0],
                "Low": [8.0, 8.0, 8.0, 8.0],
                "Close": [10.0, 9.0, 9.0, 10.0],
            }
        )
        for include_running in ("YES", "NO"):
            with (
                self.subTest(include_running=include_running),
                patch.object(sysmktpxy, "SYSMKTPXY_DEBUG_ENABLED", False),
                patch.object(
                    sysdthapxy,
                    "SYSDTHAPXY_INCLUDE_RUNNING_CANDLE",
                    include_running,
                ),
            ):
                expected = sysmktpxy.get_signal(frame)
                signal, _, ce_depth, pe_depth = sysdptpxy.detect_pxy_flip_signal(frame)
                expected_display_signal = expected[0] if expected[0] != "NONE" else expected[1]
                self.assertEqual(signal, expected_display_signal)
                self.assertEqual((ce_depth, pe_depth), (1, 1))

    def test_depth_uses_same_three_candle_window_as_market_signal(self):
        frame = pd.DataFrame(
            {
                "Open": [9.0, 10.0, 9.0, 10.0],
                "High": [11.0, 11.0, 11.0, 11.0],
                "Low": [8.0, 8.0, 8.0, 8.0],
                "Close": [10.0, 9.0, 10.0, 9.0],
            }
        )
        with (
            patch.object(sysmktpxy, "SYSMKTPXY_DEBUG_ENABLED", False),
            patch.object(sysdthapxy, "SYSDTHAPXY_INCLUDE_RUNNING_CANDLE", "NO"),
        ):
            self.assertEqual(sysmktpxy.get_signal(frame), ("BUY", "BULL"))
            signal, _, ce_depth, pe_depth = sysdptpxy.detect_pxy_flip_signal(frame)
        self.assertEqual(signal, "BUY")
        self.assertEqual((ce_depth, pe_depth), (1, 1))

    def test_depth_streak_excludes_running_candle_when_configured(self):
        closes = [10.0, 8.0, 9.0, 7.0]
        frame = pd.DataFrame(
            {
                "Open": closes,
                "High": [value + 1 for value in closes],
                "Low": [value - 1 for value in closes],
                "Close": closes,
            }
        )
        expected = {
            "YES": (("SELL", "BEAR"), "SELL", 1, 1),
            "NO": (("BUY", "BULL"), "BUY", 1, 1),
        }
        for include_running, (market, depth_signal, ce_depth, pe_depth) in expected.items():
            with (
                self.subTest(include_running=include_running),
                patch.object(sysmktpxy, "SYSMKTPXY_DEBUG_ENABLED", False),
                patch.object(
                    sysdthapxy,
                    "SYSDTHAPXY_INCLUDE_RUNNING_CANDLE",
                    include_running,
                ),
            ):
                self.assertEqual(sysmktpxy.get_signal(frame), market)
                signal, _, actual_ce_depth, actual_pe_depth = (
                    sysdptpxy.detect_pxy_flip_signal(frame)
                )
                self.assertEqual(signal, depth_signal)
                self.assertEqual((actual_ce_depth, actual_pe_depth), (ce_depth, pe_depth))

    def test_entry_router_has_selectable_mkt_sts_mode(self):
        from syscnfgpxy import (
            SYSENTRPXY_SIGNAL_MODE,
            SYSDTAFPXY_SELECTED_MODE,
            SYSDTHAPXY_INCLUDE_RUNNING_CANDLE,
            SYSMKTPXY_INCLUDE_RUNNING_CANDLE,
        )

        self.assertEqual(SYSENTRPXY_SIGNAL_MODE, "MKT")
        self.assertEqual(SYSDTAFPXY_SELECTED_MODE, "6")
        self.assertEqual(SYSDTHAPXY_INCLUDE_RUNNING_CANDLE, "YES")
        self.assertEqual(SYSMKTPXY_INCLUDE_RUNNING_CANDLE, SYSDTHAPXY_INCLUDE_RUNNING_CANDLE)
        self.assertEqual(
            __import__("pxyconfigwebpxy").ENUMS["SYSDTHAPXY_INCLUDE_RUNNING_CANDLE"],
            ("YES", "NO"),
        )
        self.assertEqual(sysentrpxy.get_entry_signal.__defaults__, (None, None))
        self.assertIn("SYSENTRPXY_SIGNAL_MODE", __import__("pxyconfigwebpxy").ENUMS)
        self.assertFalse(entry_signal_valid("SIDE"))
        self.assertIsNone(entry_order_command("SIDE", 0, 0))

    def test_average_dashboard_displays_target_after_run(self):
        with redirect_stdout(StringIO()) as output:
            exeavxpxy.print_telemetry_dashboard({
                "ce_lots": 1, "ce_lgt": -10, "ce_run_pct": 2,
                "ce_tgt": 15, "ce_pnl": 183,
                "pe_lots": 1, "pe_lgt": -39, "pe_run_pct": -7,
                "pe_tgt": 22, "pe_pnl": -677,
                "ce_investment": 1000, "pe_investment": 1200,
            })

        lines = [
            re.sub(r"\x1b\[[0-9;]*m", "", line)
            for line in output.getvalue().splitlines()
        ]
        self.assertTrue(any("RUN  TGT" in line for line in lines))
        ce_row = next(line for line in lines if line.strip().startswith("CE"))
        self.assertEqual(ce_row.split(), ["CE", "1", "-10", "2", "15", "183"])

    def test_open_position_entry_message_ends_with_skipped(self):
        def dispatch(name, provider, *args, **kwargs):
            if name == "engine_window_open":
                return True
            if name == "is_entry_blackout":
                return False
            return provider(*args, **kwargs)

        with (
            patch.object(exeentrpxy, "dispatch_mode", side_effect=dispatch),
            patch.object(exeentrpxy, "get_all_data", return_value={"entry": "BUY"}),
            patch.object(exeentrpxy, "get_session", return_value=object()),
            patch.object(exeentrpxy, "get_position_summary", return_value="1CE1PE"),
            redirect_stdout(StringIO()) as output,
        ):
            exeentrpxy.main()

        self.assertIn("Position open (CE:1, PE:1); skipped", output.getvalue())
        self.assertNotIn("entry skipped", output.getvalue())

    def test_forced_buy_passes_configured_otm_distance_to_symbol_builder(self):
        with (
            patch.object(exeforcepxy, "get_session", return_value=object()),
            patch.object(exeforcepxy, "get_all_data", return_value={"price": 23456}),
            patch.object(exeforcepxy, "get_dynamic_otm_distance", return_value=100),
            patch.object(exeforcepxy, "get_symbol", return_value="NIFTY26O23550PE") as get_symbol,
            patch.object(exeforcepxy, "execute_order", return_value={"stat": "OK"}),
            patch.object(exeforcepxy, "get_available_funds", return_value=100000),
        ):
            exeforcepxy.run_action("2")

        get_symbol.assert_called_once_with(23456, "OTMSELL", 100)

    def test_action_cooldowns_share_the_central_seven_second_setting(self):
        self.assertEqual(SYSCNFGPXY_ACTION_COOLDOWN_SECONDS, 7)
        self.assertEqual(exeacgpxy.COOL_DOWN_SECONDS, SYSCNFGPXY_ACTION_COOLDOWN_SECONDS)
        self.assertEqual(execbuypxy.CBUY_LOCK_SECS, SYSCNFGPXY_ACTION_COOLDOWN_SECONDS)
        self.assertEqual(exeexitpxy.EXIT_LOCK_SECS, SYSCNFGPXY_ACTION_COOLDOWN_SECONDS)

    def test_counter_buy_uses_exit_signal_only(self):
        import syscnfgpxy

        self.assertFalse(hasattr(syscnfgpxy, "EXECBUYPXY_ENTRY_KEY_COLUMN"))
        self.assertEqual(execbuypxy.EXIT_KEY_COLUMN, "exit")
        scripts = {"CE": "pxybuype", "PE": "pxybuyce"}
        pe_positions = [
            {"symbol": "NIFTY-1PE", "qty": 75},
            {"symbol": "NIFTY-2PE", "qty": 75},
        ]
        ce_positions = [
            {"symbol": "NIFTY-1CE", "qty": 75},
            {"symbol": "NIFTY-2CE", "qty": 75},
        ]

        self.assertEqual(
            counter_leg_script("BULL", pe_positions, scripts),
            "pxybuyce",
        )
        self.assertEqual(
            counter_leg_script("BEAR", ce_positions, scripts),
            "pxybuype",
        )
        self.assertIsNone(
            counter_leg_script("NONE", pe_positions, scripts)
        )
        self.assertIsNone(
            counter_leg_script("BUY", pe_positions, scripts)
        )
        self.assertIsNone(
            counter_leg_script("SELL", pe_positions, scripts)
        )

    def test_tgt_uses_exit_key_and_option_side_only(self):
        self.assertEqual(exeltgtpxy.calculate_tgt(True), 77.0)
        self.assertEqual(exeltgtpxy.calculate_tgt(False), 1.4)
        ce = {
            "pxy_entry": 1000, "symbol": "NIFTYCE", "exit": "BULL",
            "direction": "DOWN", "supertrend": "SIDE",
        }
        pe = {
            "pxy_entry": 1000, "symbol": "NIFTYPE", "exit": "BEAR",
            "direction": "UP", "supertrend": "SIDE",
        }
        self.assertEqual(exeltgtpxy.target_price(ce, 1000, 5000), 1770.0)
        self.assertEqual(exeltgtpxy.target_price(pe, 5000, 1000), 1770.0)
        self.assertEqual(exeltgtpxy.target_price({**ce, "exit": "BEAR"}), 1014.0)
        self.assertEqual(exeltgtpxy.target_price({**pe, "exit": "BULL"}), 1014.0)
        self.assertEqual(exeltgtpxy.target_price({**ce, "exit": "SIDE"}), 1014.0)

    def test_averaging_alignment_uses_exit_signal_only(self):
        self.assertEqual(exeavxpxy.averaging_alignment_signals("BULL"), (True, False))
        self.assertEqual(exeavxpxy.averaging_alignment_signals("BEAR"), (False, True))
        self.assertEqual(exeavxpxy.averaging_alignment_signals("SIDE"), (False, False))

    def test_lgt_scales_base_fifty_by_investment_ratio(self):
        self.assertEqual(exeltgtpxy.calculate_lgt(1000.0, 4000.0, is_ce=True), -12.5)
        self.assertEqual(exeltgtpxy.calculate_lgt(2000.0, 4000.0, is_ce=True), -25.0)
        self.assertEqual(exeltgtpxy.calculate_lgt(1000.0, 1000.0, is_ce=True), -50.0)
        self.assertEqual(exeltgtpxy.calculate_lgt(2000.0, 1000.0, is_ce=True), -77.0)
        self.assertEqual(exeltgtpxy.calculate_lgt(3000.0, 1000.0, is_ce=True), -77.0)
        self.assertEqual(exeltgtpxy.calculate_lgt(1000.0, 4000.0, is_ce=False), -77.0)
        self.assertEqual(exeltgtpxy.calculate_lgt(0.0, 4000.0, is_ce=True), -50.0)

    def test_averaging_requires_both_losing_sides_and_only_aligned_side_triggers(self):
        shared = {
            "ce_aligned": True,
            "pe_aligned": False,
            "ce_rows": 8,
            "pe_rows": 8,
            "ce_investment": 2000,
            "pe_investment": 4000,
            "ce_cooling": False,
            "pe_cooling": False,
            "ce_loss": -10,
            "pe_loss": -20,
            "ce_threshold": -5,
            "pe_threshold": -5,
            "max_investment": EXEAMSPXY_MAX_INVESTMENT,
            "ce_next_investment": 1000,
            "pe_next_investment": 1000,
        }

        self.assertEqual(averaging_trigger_sides(**shared), {"CE": True, "PE": False})

        no_opposite_loss = averaging_trigger_sides(**{**shared, "pe_loss": 0})
        no_opposite_position = averaging_trigger_sides(**{**shared, "pe_rows": 0})
        aligned_pe = averaging_trigger_sides(
            **{**shared, "ce_aligned": False, "pe_aligned": True}
        )
        over_value_cap = averaging_trigger_sides(
            **{**shared, "ce_investment": 24500, "ce_next_investment": 1000}
        )

        self.assertEqual(no_opposite_loss, {"CE": False, "PE": False})
        self.assertEqual(no_opposite_position, {"CE": False, "PE": False})
        self.assertEqual(aligned_pe, {"CE": False, "PE": True})
        self.assertEqual(over_value_cap, {"CE": False, "PE": False})

    def test_value_cap_is_fixed_at_twenty_five_thousand_without_layer_mode(self):
        self.assertEqual(EXEAMSPXY_MAX_INVESTMENT, 25000.0)

    def test_renko_uses_configured_brick_size_by_default(self):
        frame = pd.DataFrame(
            {
                "Open": [100.0, 105.0],
                "High": [100.0, 105.0],
                "Low": [100.0, 105.0],
                "Close": [100.0, 105.0],
            }
        )
        result = apply_ohlc_transformation(frame, mode=8)

        self.assertEqual(SYSDTAFPXY_FIXED_BRICK_SIZE, 2.5)
        self.assertEqual(result["Close"].tolist(), [102.5, 105.0])

    def test_heikin_ashi_mode_transforms_ohlc_sequentially(self):
        frame = pd.DataFrame(
            {
                "Open": [10.0, 12.0],
                "High": [14.0, 16.0],
                "Low": [8.0, 10.0],
                "Close": [12.0, 14.0],
            }
        )

        result = apply_ohlc_transformation(frame, mode=6)

        self.assertEqual(result["Close"].tolist(), [11.0, 13.0])
        self.assertEqual(result["Open"].tolist(), [10.0, 10.5])
        self.assertEqual(result["High"].tolist(), [14.0, 16.0])
        self.assertEqual(result["Low"].tolist(), [8.0, 10.0])

    def test_renko_respects_per_call_brick_size(self):
        frame = pd.DataFrame(
            {
                "Open": [100.0, 105.0],
                "High": [100.0, 105.0],
                "Low": [100.0, 105.0],
                "Close": [100.0, 105.0],
            }
        )
        result = apply_ohlc_transformation(
            frame, mode=8, fixed_brick_size=5.0
        )

        self.assertEqual(result["Close"].tolist(), [105.0])

    def test_data_timezone_uses_shared_setting(self):
        from sysdtafpxy import TIMEZONE

        self.assertEqual(TIMEZONE, str(SYSCNFGPXY_TIMEZONE))

    def test_atm_mode_overrides_otm_buy_request_and_supplied_distance(self):
        with (
            patch.object(exeotmpxy.syscnfgpxy, "EXEOTMPXY_STRIKE_MODE", "ATM"),
            patch.object(runniftypxy, "get_target_tuesday", return_value=date(2026, 10, 13)),
        ):
            symbol = runniftypxy.get_symbol(23456, "OTMBUY", 200)

        self.assertTrue(symbol.endswith("23450CE"))

    def test_fixed_and_dynamic_modes_control_ce_and_pe_strikes(self):
        with (
            patch.object(exeotmpxy.syscnfgpxy, "EXEOTMPXY_STRIKE_MODE", "OTMFIX"),
            patch.object(exeotmpxy.syscnfgpxy, "EXEOTMPXY_FIXED_DISTANCE", 100),
            patch.object(runniftypxy, "get_target_tuesday", return_value=date(2026, 10, 13)),
        ):
            fixed_ce = runniftypxy.get_symbol(23456, "OTMBUY", 999)
            fixed_pe = runniftypxy.get_symbol(23456, "OTMSELL", 999)

        self.assertTrue(fixed_ce.endswith("23550CE"))
        self.assertTrue(fixed_pe.endswith("23350PE"))

        distances = []
        with patch.object(exeotmpxy.syscnfgpxy, "EXEOTMPXY_STRIKE_MODE", "OTMDYN"):
            for day in range(5):
                distances.append(
                    exeotmpxy.get_dynamic_otm_distance(
                        date(2026, 10, 5) + timedelta(days=day)
                    )
                )
        self.assertEqual(distances, [200, 150, 100, 50, 0])

    def test_dynamic_strike_mode_rejects_weekends(self):
        with patch.object(exeotmpxy.syscnfgpxy, "EXEOTMPXY_STRIKE_MODE", "OTMDYN"):
            with self.assertRaises(ValueError):
                exeotmpxy.get_dynamic_otm_distance(date(2026, 10, 4))

    def test_atr_depth_floor_and_true_atr_fallback_are_configurable(self):
        with (
            patch.object(syskatrpxy, "SYSKATRPXY_DEPTH_ATR_MINIMUM", 8),
            patch.object(syskatrpxy, "SYSKATRPXY_TRUE_ATR_FALLBACK_VALUE", 7.0),
        ):
            depth_floor = syskatrpxy.scale_atr_value_from_depth("", 0, 0, 0, 0)
            true_atr_fallback = syskatrpxy.calculate_true_atr(pd.DataFrame())

        self.assertEqual(depth_floor, 8)
        self.assertEqual(true_atr_fallback, 7.0)


if __name__ == "__main__":
    unittest.main()
