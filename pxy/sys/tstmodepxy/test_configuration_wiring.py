import re
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import date, timedelta
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
import syscseqpxy
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
    SYSSTRNDPXY_ST1_ATR_PERIOD,
    SYSSTRNDPXY_ST1_FACTOR,
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
from systrcalpxy import _calculate_wilder_atr, _compute_single_st


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

    def test_supertrend_uses_wilder_true_range_atr(self):
        index = pd.date_range("2026-10-07", periods=3, freq="min")
        frame = pd.DataFrame(
            {
                "Open": [99.0, 100.0, 101.0],
                "High": [101.0, 105.0, 103.0],
                "Low": [98.0, 99.0, 100.0],
                "Close": [100.0, 101.0, 102.0],
            },
            index=index,
        )
        atr_period = SYSSTRNDPXY_ST1_ATR_PERIOD
        factor = SYSSTRNDPXY_ST1_FACTOR
        self.assertEqual(atr_period, 10)
        self.assertEqual(factor, 3.0)

        atr_series = _calculate_wilder_atr(frame, atr_period)
        for actual, expected in zip(atr_series, [3.0, 3.3, 3.27]):
            self.assertAlmostEqual(actual, expected)

        single_line, _, _, _ = _compute_single_st(
            frame, factor=factor, atr_period=atr_period
        )
        first_hl2 = (frame["High"].iloc[0] + frame["Low"].iloc[0]) / 2
        self.assertEqual(
            single_line.iloc[0],
            first_hl2 + factor * atr_series.iloc[0],
        )

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
                "get_signal_depth_analysis",
                return_value={
                    "signal": "BULL",
                    "past_depth": "NA",
                    "ce_depth": 1,
                    "pe_depth": 1,
                    "signal_candle_time": "2025-01-06 10:00:00",
                },
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

    def test_bull_supertrend_and_bear_mkt_in_atr_zone_give_buy_entry(self):
        frame = pd.DataFrame({"Close": [101.5]})
        with (
            patch.object(sysentrpxy, "get_market_signal", return_value="BEAR") as market,
            patch.object(
                sysentrpxy,
                "calculate_supertrend",
                return_value=pd.DataFrame({
                    "ST_Trend": ["BULL"],
                    "Close": [101.5],
                    "st_line": [100.0],
                    "st_atr": [1.0],
                }),
            ),
        ):
            self.assertEqual(
                sysentrpxy.get_entry_signal(frame),
                ("BUY", "BULL"),
            )
        market.assert_called_once_with(frame)

    def test_bear_supertrend_and_bull_mkt_in_atr_zone_give_sell_entry(self):
        frame = pd.DataFrame({"Close": [98.5]})
        with (
            patch.object(sysentrpxy, "get_market_signal", return_value="BULL") as market,
            patch.object(
                sysentrpxy,
                "calculate_supertrend",
                return_value=pd.DataFrame({
                    "ST_Trend": ["BEAR"],
                    "Close": [98.5],
                    "st_line": [100.0],
                    "st_atr": [1.0],
                }),
            ),
        ):
            self.assertEqual(
                sysentrpxy.get_entry_signal(frame),
                ("SELL", "BEAR"),
            )
        market.assert_called_once_with(frame)

    def test_countertrend_entries_are_filtered_outside_atr_zones(self):
        cases = (
            ("BULL", "BEAR", 101.5001),
            ("BULL", "BEAR", 99.9999),
            ("BEAR", "BULL", 98.4999),
            ("BEAR", "BULL", 100.0001),
        )
        for trend, market_signal, price in cases:
            frame = pd.DataFrame({"Close": [price]})
            with (
                self.subTest(trend=trend, price=price),
                patch.object(sysentrpxy, "get_market_signal", return_value=market_signal),
                patch.object(
                    sysentrpxy,
                    "calculate_supertrend",
                    return_value=pd.DataFrame({
                        "ST_Trend": [trend],
                        "Close": [price],
                        "st_line": [100.0],
                        "st_atr": [1.0],
                    }),
                ),
            ):
                expected = ("NONE", trend)
                self.assertEqual(sysentrpxy.get_entry_signal(frame), expected)

    def test_countertrend_entries_are_filtered_without_opposing_mkt(self):
        frame = pd.DataFrame({"Close": [100.5]})
        for trend, market_signal in (("BULL", "BULL"), ("BEAR", "BEAR")):
            with (
                self.subTest(trend=trend),
                patch.object(sysentrpxy, "get_market_signal", return_value=market_signal),
                patch.object(
                    sysentrpxy,
                    "calculate_supertrend",
                    return_value=pd.DataFrame({
                        "ST_Trend": [trend],
                        "Close": [100.5],
                        "st_line": [100.0],
                        "st_atr": [1.0],
                    }),
                ),
            ):
                self.assertEqual(
                    sysentrpxy.get_entry_signal(frame),
                    ("NONE", trend),
                )

    def test_countertrend_zone_width_tracks_half_supertrend_factor(self):
        frame = pd.DataFrame({"Close": [102.0]})
        with (
            patch.object(sysentrpxy, "SYSSTRNDPXY_ST1_FACTOR", 4.0),
            patch.object(sysentrpxy, "get_market_signal", return_value="BEAR"),
            patch.object(
                sysentrpxy,
                "calculate_supertrend",
                return_value=pd.DataFrame({
                    "ST_Trend": ["BULL"],
                    "Close": [102.0],
                    "st_line": [100.0],
                    "st_atr": [1.0],
                }),
            ),
        ):
            self.assertEqual(sysentrpxy.get_entry_signal(frame), ("BUY", "BULL"))

    def test_side_supertrend_returns_none_entry_and_mkt_exit(self):
        frame = pd.DataFrame({"Close": [1]})
        with (
            patch.object(sysentrpxy, "get_market_signal", return_value="BEAR") as market,
            patch.object(
                sysentrpxy,
                "calculate_supertrend",
                return_value=pd.DataFrame({"ST_Trend": ["SIDE"]}),
            ),
        ):
            self.assertEqual(
                sysentrpxy.get_entry_signal(frame),
                ("NONE", "BEAR"),
            )
        market.assert_called_once_with(frame)

    def test_side_supertrend_normalizes_non_directional_mkt_signal_to_none(self):
        frame = pd.DataFrame({"Close": [1]})
        with (
            patch.object(sysentrpxy, "get_market_signal", return_value="NONE"),
            patch.object(
                sysentrpxy,
                "calculate_supertrend",
                return_value=pd.DataFrame({"ST_Trend": ["SIDE"]}),
            ),
        ):
            self.assertEqual(sysentrpxy.get_entry_signal(frame), ("NONE", "NONE"))

    def test_side_lower_quarter_with_bear_mkt_gives_buy_entry(self):
        frame = pd.DataFrame({"Close": [12.5]})
        with (
            patch.object(sysentrpxy, "get_market_signal", return_value="BEAR"),
            patch.object(
                sysentrpxy,
                "calculate_supertrend",
                return_value=pd.DataFrame({
                    "Close": [12.5],
                    "st_line": [0.0],
                    "st_mirror": [100.0],
                    "ST_Trend": ["SIDE"],
                }),
            ),
        ):
            self.assertEqual(sysentrpxy.get_entry_signal(frame), ("BUY", "BEAR"))

    def test_side_upper_quarter_with_bull_mkt_gives_sell_entry(self):
        frame = pd.DataFrame({"Close": [87.5]})
        with (
            patch.object(sysentrpxy, "get_market_signal", return_value="BULL"),
            patch.object(
                sysentrpxy,
                "calculate_supertrend",
                return_value=pd.DataFrame({
                    "Close": [87.5],
                    "st_line": [100.0],
                    "st_mirror": [0.0],
                    "ST_Trend": ["SIDE"],
                }),
            ),
        ):
            self.assertEqual(sysentrpxy.get_entry_signal(frame), ("SELL", "BULL"))

    def test_side_entries_require_matching_market_and_outer_quarter(self):
        for price, market_signal in ((20.0, "BULL"), (80.0, "BEAR"), (50.0, "BEAR")):
            with (
                self.subTest(price=price, market_signal=market_signal),
                patch.object(sysentrpxy, "get_market_signal", return_value=market_signal),
                patch.object(
                    sysentrpxy,
                    "calculate_supertrend",
                    return_value=pd.DataFrame({
                        "Close": [price],
                        "st_line": [0.0],
                        "st_mirror": [100.0],
                        "ST_Trend": ["SIDE"],
                    }),
                ),
            ):
                self.assertEqual(
                    sysentrpxy.get_entry_signal(pd.DataFrame({"Close": [price]})),
                    ("NONE", market_signal),
                )

    def test_invalid_supertrend_state_returns_none(self):
        frame = pd.DataFrame({"Close": [1]})
        with (
            patch.object(sysentrpxy, "get_market_signal") as market,
            patch.object(
                sysentrpxy,
                "calculate_supertrend",
                return_value=pd.DataFrame({"ST_Trend": ["UNKNOWN"]}),
            ),
        ):
            self.assertEqual(sysentrpxy.get_entry_signal(frame), ("NONE", "NONE"))
        market.assert_not_called()

    def test_market_signal_returns_only_bull_bear_or_none(self):
        with (
            patch.object(sysmktpxy, "SYSMKTPXY_DEBUG_ENABLED", False),
            patch.object(sysdthapxy, "SYSDTHAPXY_INCLUDE_RUNNING_CANDLE", "YES"),
        ):
            self.assertEqual(
                sysmktpxy.get_signal(pd.DataFrame({"Close": [10.0, 8.0, 9.0]})),
                "BULL",
            )
            self.assertEqual(
                sysmktpxy.get_signal(pd.DataFrame({"Close": [8.0, 10.0, 9.0]})),
                "BEAR",
            )
            self.assertEqual(
                sysmktpxy.get_signal(pd.DataFrame({"Close": [8.0, 9.0, 10.0]})),
                "BULL",
            )
            self.assertEqual(
                sysmktpxy.get_signal(pd.DataFrame({"Close": [10.0, 9.0, 8.0]})),
                "BEAR",
            )
            for closes in ([8.0, 9.0, 9.0], [9.0, 9.0, 10.0], [9.0, 9.0, 9.0]):
                with self.subTest(closes=closes):
                    self.assertEqual(
                        sysmktpxy.get_signal(pd.DataFrame({"Close": closes})),
                        "NONE",
                    )

    def test_market_signal_requires_three_closes(self):
        with (
            patch.object(sysmktpxy, "SYSMKTPXY_DEBUG_ENABLED", False),
            patch.object(sysdthapxy, "SYSDTHAPXY_INCLUDE_RUNNING_CANDLE", "YES"),
        ):
            self.assertEqual(
                sysmktpxy.get_signal(pd.DataFrame({"Close": [10.0, 8.0]})),
                "NONE",
            )

    def test_market_signal_can_exclude_running_candle(self):
        frame = pd.DataFrame({"Close": [10.0, 8.0, 9.0, 7.0]})
        with (
            patch.object(sysmktpxy, "SYSMKTPXY_DEBUG_ENABLED", False),
            patch.object(sysdthapxy, "SYSDTHAPXY_INCLUDE_RUNNING_CANDLE", "YES"),
        ):
            self.assertEqual(sysmktpxy.get_signal(frame), "BEAR")
        with (
            patch.object(sysmktpxy, "SYSMKTPXY_DEBUG_ENABLED", False),
            patch.object(sysdthapxy, "SYSDTHAPXY_INCLUDE_RUNNING_CANDLE", "NO"),
        ):
            self.assertEqual(sysmktpxy.get_signal(frame), "BULL")
            self.assertEqual(
                sysmktpxy.get_signal(frame.iloc[:3]),
                "NONE",
            )

    def test_market_signal_delegates_to_dtha_analysis(self):
        frame = pd.DataFrame({"Close": [10.0, 8.0, 9.0]})
        with (
            patch.object(sysmktpxy, "SYSMKTPXY_DEBUG_ENABLED", False),
            patch.object(sysdthapxy, "SYSDTHAPXY_INCLUDE_RUNNING_CANDLE", "YES"),
            patch.object(
                sysmktpxy,
                "get_signal_depth_analysis",
                wraps=sysdthapxy.get_signal_depth_analysis,
            ) as analysis,
        ):
            self.assertEqual(sysmktpxy.get_signal(frame), "BULL")
        analysis.assert_called_once_with(frame)

    def test_dtha_and_mkt_return_only_bull_bear_or_none(self):
        expected_signals = {
            (10.0, 8.0, 9.0): "BULL",
            (8.0, 10.0, 9.0): "BEAR",
            (8.0, 9.0, 10.0): "BULL",
            (10.0, 9.0, 8.0): "BEAR",
            (8.0, 9.0, 9.0): "NONE",
        }
        with (
            patch.object(sysmktpxy, "SYSMKTPXY_DEBUG_ENABLED", False),
            patch.object(sysdthapxy, "SYSDTHAPXY_INCLUDE_RUNNING_CANDLE", "YES"),
        ):
            for closes, expected_signal in expected_signals.items():
                with self.subTest(closes=closes):
                    analysis = sysdthapxy.get_signal_depth_analysis(
                        pd.DataFrame({"Close": closes}),
                        include_running=True,
                    )
                    self.assertEqual(analysis["signal"], expected_signal)
                    self.assertNotIn("entry", analysis)
                    self.assertNotIn("exit", analysis)
                    self.assertEqual(
                        sysmktpxy.get_signal(pd.DataFrame({"Close": closes})),
                        expected_signal,
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

    def test_mkt_signal_tracks_reversals_and_continuations_directionally(self):
        cases = (
            ([10.0, 9.0, 8.0], "BEAR"),
            ([10.0, 9.0, 8.0, 7.0], "BEAR"),
            ([10.0, 9.0, 8.0, 7.0, 6.0], "BEAR"),
            ([10.0, 11.0, 12.0], "BULL"),
            ([10.0, 11.0, 12.0, 13.0], "BULL"),
            ([10.0, 11.0, 12.0, 13.0, 14.0], "BULL"),
            ([10.0, 9.0, 10.0, 9.0], "BEAR"),
        )
        with (
            patch.object(sysmktpxy, "SYSMKTPXY_DEBUG_ENABLED", False),
            patch.object(sysdthapxy, "SYSDTHAPXY_INCLUDE_RUNNING_CANDLE", "YES"),
        ):
            for closes, expected in cases:
                with self.subTest(closes=closes):
                    self.assertEqual(
                        sysmktpxy.get_signal(pd.DataFrame({"Close": closes})),
                        expected,
                    )

    def test_candle_visual_obeys_shared_running_candle_setting(self):
        colors = pd.Series(["green", "red"])
        with (
            patch.object(
                syscseqpxy,
                "get_pxy_data",
                return_value=(None, None, colors, None),
            ),
            patch.object(syscseqpxy, "SYSDTHAPXY_INCLUDE_RUNNING_CANDLE", "NO"),
        ):
            confirmed_visual = syscseqpxy.get_candle_visual()
        self.assertEqual(confirmed_visual, "\033[92m1\033[0m")

        with (
            patch.object(
                syscseqpxy,
                "get_pxy_data",
                return_value=(None, None, colors, None),
            ),
            patch.object(syscseqpxy, "SYSDTHAPXY_INCLUDE_RUNNING_CANDLE", "YES"),
        ):
            running_visual = syscseqpxy.get_candle_visual()
        self.assertEqual(
            running_visual,
            "\033[92m1\033[0m\033[91m1\033[0m",
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
        with patch.object(sysdthapxy, "SYSDTHAPXY_INCLUDE_RUNNING_CANDLE", "NO"):
            _, _, ce_depth, pe_depth = sysdptpxy.detect_pxy_flip_signal(df=frame)
        self.assertEqual(ce_depth, len(closes) - 2)
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
                signal, _, ce_depth, pe_depth = sysdptpxy.detect_pxy_flip_signal(frame)
                self.assertEqual(signal, sysdthapxy.get_signal_depth_analysis(
                    frame,
                    include_running=include_running == "YES",
                )["signal"])
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
            self.assertEqual(sysmktpxy.get_signal(frame), "BULL")
            signal, _, ce_depth, pe_depth = sysdptpxy.detect_pxy_flip_signal(frame)
        self.assertEqual(signal, "BULL")
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
            "YES": ("BEAR", "BEAR", 1, 1),
            "NO": ("BULL", "BULL", 1, 1),
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

    def test_depth_squareoff_requires_opposite_side_and_depth_above_six(self):
        self.assertEqual(exeexitpxy.depth_squareoff_side("BUY", "PE6"), None)
        self.assertEqual(exeexitpxy.depth_squareoff_side("BUY", "PE7"), "PE")
        self.assertEqual(exeexitpxy.depth_squareoff_side("BUY", "CE7"), None)
        self.assertEqual(exeexitpxy.depth_squareoff_side("SELL", "CE7"), "CE")
        self.assertEqual(exeexitpxy.depth_squareoff_side("SELL", "PE7"), None)
        self.assertEqual(exeexitpxy.depth_squareoff_side("SELL", "CE6"), None)
        self.assertEqual(exeexitpxy.depth_squareoff_side("BUY", "PE-7"), None)

    def test_pastrsk_switch_gates_depth_squareoff(self):
        active_orders = pd.DataFrame(
            [
                {
                    "symbol": "NIFTY-WF-PE",
                    "qty": 75,
                    "entry": "BUY",
                    "hkin_past_depth": "PE7",
                    "hkin_signal_time": "2025-01-06 10:00:00",
                }
            ]
        )
        with patch.object(exeexitpxy, "PASTRSK", "NO"):
            self.assertEqual(
                exeexitpxy.run_depth_squareoff(
                    client=None,
                    active_df=active_orders,
                    market_data_available=True,
                ),
                set(),
            )

        from syscnfgpxy import PASTRSK

        self.assertEqual(PASTRSK, "YES")
        self.assertEqual(__import__("pxyconfigwebpxy").ENUMS["PASTRSK"], ("YES", "NO"))

    def test_depth_squareoff_uses_side_command_and_only_returns_unlocked_side_lots(self):
        active_orders = pd.DataFrame(
            [
                {
                    "symbol": "NIFTY-WF-CE",
                    "tag": "CE1",
                    "buy_time": "2025-01-06 09:59:00",
                    "entry": "BUY",
                    "hkin_past_depth": "PE7",
                    "hkin_signal_time": "2025-01-06 10:00:00",
                },
                {
                    "symbol": "NIFTY-WF-PE",
                    "tag": "PE1",
                    "buy_time": "2025-01-06 09:59:00",
                    "qty": 75,
                    "buy_prc": 100.0,
                    "sell_prc": 80.0,
                    "entry": "BUY",
                    "hkin_past_depth": "PE7",
                    "hkin_signal_time": "2025-01-06 10:00:00",
                },
            ]
        )
        with (
            patch.object(exeexitpxy, "PASTRSK", "YES"),
            patch.object(exeexitpxy, "ledger_busy", return_value=False),
            patch.object(exeexitpxy, "_recently_exited", return_value=False),
            patch.object(exeexitpxy, "_mark_lock") as mark_lock,
            patch.object(exeexitpxy.subprocess, "run") as run_command,
        ):
            exited_keys = exeexitpxy.run_depth_squareoff(
                client=None,
                active_df=active_orders,
                market_data_available=True,
            )

        self.assertEqual(
            exited_keys,
            {"NIFTY-WF-PE|PE1|2025-01-06 09:59:00"},
        )
        run_command.assert_called_once_with(
            ["pxysqrpe"],
            check=True,
            timeout=exeexitpxy.SQUAREOFF_TIMEOUT_SECS,
        )
        mark_lock.assert_called_once_with(
            "DEPTH_EXIT|PE|2025-01-06 10:00:00"
        )

    def test_pastrsk_loss_filter_requires_more_than_fourteen_percent(self):
        active_orders = pd.DataFrame(
            [
                {
                    "symbol": "NIFTY-WF-PE",
                    "qty": 75,
                    "buy_prc": 100.0,
                    "sell_prc": 86.0,
                    "tag": "PE1",
                    "buy_time": "2025-01-06 09:59:00",
                    "entry": "BUY",
                    "hkin_past_depth": "PE7",
                    "hkin_signal_time": "2025-01-06 10:00:00",
                }
            ]
        )
        self.assertEqual(exeexitpxy.depth_exit_side_loss_pct(active_orders, "PE"), -14.0)

        with (
            patch.object(exeexitpxy, "PASTRSK", "YES"),
            patch.object(exeexitpxy, "ledger_busy", return_value=False),
            patch.object(exeexitpxy, "_recently_exited", return_value=False),
            patch.object(exeexitpxy, "_mark_lock"),
            patch.object(exeexitpxy.subprocess, "run") as run_command,
        ):
            self.assertEqual(
                exeexitpxy.run_depth_squareoff(
                    client=None,
                    active_df=active_orders,
                    market_data_available=True,
                ),
                set(),
            )
            run_command.assert_not_called()

            active_orders.loc[0, "sell_prc"] = 85.99
            self.assertLess(exeexitpxy.depth_exit_side_loss_pct(active_orders, "PE"), -14.0)
            self.assertEqual(
                exeexitpxy.run_depth_squareoff(
                    client=None,
                    active_df=active_orders,
                    market_data_available=True,
                ),
                {"NIFTY-WF-PE|PE1|2025-01-06 09:59:00"},
            )
            run_command.assert_called_once_with(
                ["pxysqrpe"],
                check=True,
                timeout=exeexitpxy.SQUAREOFF_TIMEOUT_SECS,
            )

        self.assertIsNone(
            exeexitpxy.depth_exit_side_loss_pct(
                active_orders.drop(columns=["sell_prc"]), "PE"
            )
        )

    def test_pastrsk_checks_ce_loss_independently_of_pe_loss(self):
        active_orders = pd.DataFrame(
            [
                {
                    "symbol": "NIFTY-WF-CE",
                    "qty": 75,
                    "buy_prc": 100.0,
                    "sell_prc": 80.0,
                    "tag": "CE1",
                    "buy_time": "2025-01-06 09:59:00",
                    "entry": "SELL",
                    "hkin_past_depth": "CE7",
                    "hkin_signal_time": "2025-01-06 10:00:00",
                },
                {
                    "symbol": "NIFTY-WF-PE",
                    "qty": 75,
                    "buy_prc": 100.0,
                    "sell_prc": 95.0,
                    "tag": "PE1",
                    "buy_time": "2025-01-06 09:59:00",
                    "entry": "SELL",
                    "hkin_past_depth": "CE7",
                    "hkin_signal_time": "2025-01-06 10:00:00",
                },
            ]
        )
        self.assertEqual(exeexitpxy.depth_exit_side_loss_pct(active_orders, "CE"), -20.0)
        self.assertEqual(exeexitpxy.depth_exit_side_loss_pct(active_orders, "PE"), -5.0)

        with (
            patch.object(exeexitpxy, "PASTRSK", "YES"),
            patch.object(exeexitpxy, "ledger_busy", return_value=False),
            patch.object(exeexitpxy, "_recently_exited", return_value=False),
            patch.object(exeexitpxy, "_mark_lock"),
            patch.object(exeexitpxy.subprocess, "run") as run_command,
        ):
            exited_keys = exeexitpxy.run_depth_squareoff(
                client=None,
                active_df=active_orders,
                market_data_available=True,
            )

        self.assertEqual(
            exited_keys,
            {"NIFTY-WF-CE|CE1|2025-01-06 09:59:00"},
        )
        run_command.assert_called_once_with(
            ["pxysqrce"],
            check=True,
            timeout=exeexitpxy.SQUAREOFF_TIMEOUT_SECS,
        )

    def test_entry_router_has_no_signal_mode_switch(self):
        from syscnfgpxy import (
            SYSDTHAPXY_INCLUDE_RUNNING_CANDLE,
        )

        self.assertEqual(SYSDTHAPXY_INCLUDE_RUNNING_CANDLE, "YES")
        self.assertEqual(
            __import__("pxyconfigwebpxy").ENUMS["SYSDTHAPXY_INCLUDE_RUNNING_CANDLE"],
            ("YES", "NO"),
        )
        self.assertEqual(sysentrpxy.get_entry_signal.__defaults__, (None,))
        self.assertNotIn("SYSENTRPXY_SIGNAL_MODE", __import__("pxyconfigwebpxy").ENUMS)
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

    def test_action_cooldowns_share_the_central_six_second_setting(self):
        import syscnfgpxy

        self.assertEqual(SYSCNFGPXY_ACTION_COOLDOWN_SECONDS, 6)
        self.assertEqual(exeacgpxy.COOL_DOWN_SECONDS, SYSCNFGPXY_ACTION_COOLDOWN_SECONDS)
        self.assertEqual(execbuypxy.CBUY_LOCK_SECS, SYSCNFGPXY_ACTION_COOLDOWN_SECONDS)
        self.assertEqual(exeexitpxy.EXIT_LOCK_SECS, SYSCNFGPXY_ACTION_COOLDOWN_SECONDS)
        self.assertEqual(syscnfgpxy.EXEPXYPXY_IDLE_PAUSE_SECONDS, 6)
        self.assertEqual(exeexitpxy.SQOFF_MIN_GAP_SECS, 6)
        self.assertEqual(syscnfgpxy.EXESQRPXY_POST_EXIT_COOLDOWN_SECONDS, 6)

    def test_counter_buy_routes_from_exit_signal_and_held_side(self):
        import syscnfgpxy

        self.assertFalse(hasattr(syscnfgpxy, "EXECBUYPXY_ENTRY_KEY_COLUMN"))
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
            counter_leg_script("BULL", pe_positions + ce_positions, scripts)
        )
        self.assertIsNone(counter_leg_script("BEAR", pe_positions, scripts))
        self.assertIsNone(counter_leg_script("BULL", ce_positions, scripts))
        self.assertIsNone(counter_leg_script("SIDE", pe_positions, scripts))

    def test_counter_buy_dispatch_uses_exit_signal_without_loss_gate(self):
        with (
            patch.object(execbuypxy, "_load_locks", return_value={}),
            patch.object(
                execbuypxy,
                "counter_leg_permission_status",
                return_value="allowed",
            ),
            patch.object(execbuypxy, "_find_script", return_value="/tmp/pxybuyce"),
            patch.object(execbuypxy, "_is_executable", return_value=True),
            patch.object(execbuypxy, "_mark_lock") as mark_lock,
            patch.object(execbuypxy, "_count_fire") as count_fire,
            patch.object(execbuypxy.subprocess, "Popen") as popen,
        ):
            pe_hold_bull_exit = pd.DataFrame(
                [{
                    "symbol": "NIFTY-1PE", "qty": 75,
                    "exit": "BULL",
                }]
            )
            self.assertEqual(
                execbuypxy.check_counter_leg(pe_hold_bull_exit),
                "pxybuyce",
            )
            popen.assert_called_once_with(["/tmp/pxybuyce"])
            mark_lock.assert_called_once()
            count_fire.assert_called_once()

            no_matching_exit = pd.DataFrame(
                [{"symbol": "NIFTY-1PE", "qty": 75, "exit": "BEAR"}]
            )
            self.assertIsNone(execbuypxy.check_counter_leg(no_matching_exit))
            popen.assert_called_once()

    def test_aligned_tgt_uses_maximum_of_atr_depth_and_atr_power(self):
        self.assertEqual(exeltgtpxy.calculate_tgt(True, 10, 2, 3), 20.0)
        self.assertEqual(exeltgtpxy.calculate_tgt(True, 5, 3, 4), 15.0)
        self.assertEqual(exeltgtpxy.calculate_tgt(False), 1.4)
        ce = {
            "pxy_entry": 1000, "symbol": "NIFTYCE", "exit": "BULL",
            "direction": "DOWN", "supertrend": "SIDE", "atr": 10,
            "ce_power": 2, "hkin_ce_depth": 3,
        }
        pe = {
            "pxy_entry": 1000, "symbol": "NIFTYPE", "exit": "BEAR",
            "direction": "UP", "supertrend": "SIDE", "atr": 8,
            "pe_power": 3, "hkin_pe_depth": 4,
        }
        self.assertEqual(exeltgtpxy.target_price(ce, 1000, 5000), 1200.0)
        self.assertEqual(exeltgtpxy.target_price(pe, 5000, 1000), 1240.0)
        self.assertEqual(exeltgtpxy.target_price({**ce, "exit": "BEAR"}), 1014.0)
        self.assertEqual(exeltgtpxy.target_price({**pe, "exit": "BULL"}), 1014.0)
        self.assertEqual(exeltgtpxy.target_price({**ce, "exit": "SIDE"}), 1014.0)

    def test_averaging_alignment_uses_exit_signal_only(self):
        self.assertEqual(exeavxpxy.averaging_alignment_signals("BULL"), (True, False))
        self.assertEqual(exeavxpxy.averaging_alignment_signals("BEAR"), (False, True))
        self.assertEqual(exeavxpxy.averaging_alignment_signals("SIDE"), (False, False))

    def test_lgt_scales_index_price_by_investment_ratio(self):
        self.assertEqual(
            exeltgtpxy.calculate_lgt(1000.0, 4000.0, is_ce=True, index_price=25000),
            -6.25,
        )
        self.assertEqual(
            exeltgtpxy.calculate_lgt(2000.0, 4000.0, is_ce=True, index_price=25000),
            -12.5,
        )
        self.assertEqual(
            exeltgtpxy.calculate_lgt(1000.0, 1000.0, is_ce=True, index_price=25000),
            -25.0,
        )
        self.assertEqual(
            exeltgtpxy.calculate_lgt(2000.0, 1000.0, is_ce=True, index_price=25000),
            -50.0,
        )
        self.assertEqual(
            exeltgtpxy.calculate_lgt(3000.0, 1000.0, is_ce=True, index_price=25000),
            -75.0,
        )
        self.assertEqual(
            exeltgtpxy.calculate_lgt(4000.0, 1000.0, is_ce=True, index_price=25000),
            -77.0,
        )
        self.assertEqual(
            exeltgtpxy.calculate_lgt(1000.0, 4000.0, is_ce=False, index_price=25000),
            -77.0,
        )
        self.assertEqual(
            exeltgtpxy.calculate_lgt(0.0, 4000.0, is_ce=True, index_price=25000),
            -25.0,
        )
        self.assertEqual(
            exeltgtpxy.calculate_lgt(1000.0, 1000.0, is_ce=True, index_price=1000),
            -1.4,
        )
        with self.assertRaises(ValueError):
            exeltgtpxy.calculate_lgt(1000.0, 1000.0, is_ce=True, index_price=0)

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

    def test_dtaf_mode_one_averages_each_ohlc_value_with_futures_price(self):
        frame = pd.DataFrame(
            {
                "Open": [100.0, 105.0],
                "High": [102.0, 107.0],
                "Low": [98.0, 103.0],
                "Close": [101.0, 106.0],
            }
        )
        result = apply_ohlc_transformation(frame, mode=1, futures_price=200.0)

        expected = pd.DataFrame(
            {
                "Open": [150.0, 152.5],
                "High": [151.0, 153.5],
                "Low": [149.0, 151.5],
                "Close": [150.5, 153.0],
            }
        )
        pd.testing.assert_frame_equal(result, expected)
        self.assertIsNot(result, frame)

    def test_dtaf_without_futures_price_keeps_ohlc_values(self):
        frame = pd.DataFrame(
            {
                "Open": [100.0],
                "High": [102.0],
                "Low": [98.0],
                "Close": [101.0],
            }
        )
        pd.testing.assert_frame_equal(
            apply_ohlc_transformation(frame, mode=1), frame
        )

    def test_dtaf_rejects_modes_other_than_one(self):
        frame = pd.DataFrame(
            {
                "Open": [100.0],
                "High": [102.0],
                "Low": [98.0],
                "Close": [101.0],
            }
        )

        with self.assertRaisesRegex(ValueError, "only supports mode 1"):
            apply_ohlc_transformation(frame, mode=8)

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

    def test_true_atr_expands_from_first_0916_candle_then_rolls_14(self):
        index = pd.date_range(
            "2026-10-07 09:15",
            periods=16,
            freq="min",
            tz="Asia/Kolkata",
        )
        candle_ranges = [200.0] + [float(value) for value in range(1, 16)]
        frame = pd.DataFrame(
            {
                "High": [100.0 + value / 2 for value in candle_ranges],
                "Low": [100.0 - value / 2 for value in candle_ranges],
                "Close": [0.0] + [100.0] * (len(index) - 1),
            },
            index=index,
        )

        self.assertEqual(syskatrpxy.SYSKATRPXY_TRUE_ATR_PERIOD, 14)
        atr_series = syskatrpxy.calculate_atr(frame)
        self.assertEqual(atr_series.iloc[0], syskatrpxy.SYSKATRPXY_TRUE_ATR_FALLBACK_VALUE)
        self.assertEqual(atr_series.iloc[1], 1.0)
        self.assertEqual(atr_series.iloc[2], 1.5)
        self.assertEqual(syskatrpxy.calculate_true_atr(frame.iloc[:2]), 1.0)
        self.assertEqual(syskatrpxy.calculate_true_atr(frame.iloc[:3]), 1.5)
        self.assertEqual(syskatrpxy.calculate_true_atr(frame.iloc[:15]), 7.5)
        self.assertEqual(syskatrpxy.calculate_true_atr(frame), 8.5)

    def test_true_atr_resets_at_each_session_open(self):
        index = pd.DatetimeIndex(
            [
                "2026-10-06 09:16",
                "2026-10-06 09:17",
                "2026-10-07 09:15",
                "2026-10-07 09:16",
            ],
            tz="Asia/Kolkata",
        )
        frame = pd.DataFrame(
            {
                "High": [150.0, 150.0, 100.0, 101.0],
                "Low": [50.0, 50.0, 100.0, 99.0],
                "Close": [100.0, 100.0, 100.0, 100.0],
            },
            index=index,
        )

        self.assertEqual(syskatrpxy.calculate_true_atr(frame), 2.0)


if __name__ == "__main__":
    unittest.main()
