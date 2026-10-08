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
import syspxy
import sysstrndpxy
import runniftypxy
from syscnfgpxy import (
    SYSCNFGPXY_ACTION_COOLDOWN_SECONDS,
    SYSCNFGPXY_TIMEZONE,
    SYSSTRNDPXY_ST1_ATR_VALUE,
    SYSSTRNDPXY_ST1_FACTOR,
    SYSDTAFPXY_FIXED_BRICK_SIZE,
    SYSSMAPXY_VARIANT,
    SYSSTRNDPXY_CHART_TARGET_ROWS,
    EXEAVXPXY_COUNTER_TREND_LOSS_MULTIPLIER,
    EXEAMSPXY_MAX_INVESTMENT,
    EXECBUYPXY_ENTRY_KEY_COLUMN,
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

    def test_mkt_mode_uses_market_direction_for_both_signals_all_session(self):
        frame = pd.DataFrame({"Close": [1]})
        with (
            patch.object(sysentrpxy, "SYSENTRPXY_SIGNAL_MODE", "MKT"),
            patch.object(
                sysentrpxy, "detect_raw_direction", return_value=(123, "DOWN")
            ) as direction,
            patch.object(sysentrpxy, "calculate_supertrend") as supertrend,
        ):
            self.assertEqual(
                sysentrpxy.get_entry_signal(frame, current_time=time(12, 0)),
                ("SELL", "BEAR"),
            )
        direction.assert_called_once_with(frame)
        supertrend.assert_not_called()

    def test_entry_router_has_selectable_mkt_sts_mode(self):
        from syscnfgpxy import SYSENTRPXY_SIGNAL_MODE

        self.assertEqual(SYSENTRPXY_SIGNAL_MODE, "MKT")
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

    def test_counter_buy_uses_entry_signal_key(self):
        self.assertEqual(EXECBUYPXY_ENTRY_KEY_COLUMN, "entry")
        self.assertEqual(execbuypxy.ENTRY_KEY_COLUMN, "entry")

    def test_dirgt_counter_buy_uses_direction_when_heavy_side_has_multiple_rows(self):
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
            counter_leg_script(
                "SELL", pe_positions, scripts, direction="UP", mode="DIRGT"
            ),
            "pxybuyce",
        )
        self.assertEqual(
            counter_leg_script(
                "NONE", ce_positions, scripts, direction="DOWN", mode="DIRGT"
            ),
            "pxybuype",
        )
        self.assertIsNone(
            counter_leg_script(
                "NONE", pe_positions[:1], scripts, direction="UP", mode="DIRGT"
            )
        )
        self.assertIsNone(
            counter_leg_script(
                "NONE", pe_positions, scripts, direction="UP", mode="RGLR"
            )
        )
        self.assertIsNone(
            counter_leg_script(
                "BUY", pe_positions, scripts, direction="DOWN", mode="DIRGT"
            )
        )
        self.assertIsNone(
            counter_leg_script(
                "BUY", pe_positions, scripts, direction="NONE", mode="DIRGT"
            )
        )

    def test_tgt_uses_single_positive_aligned_and_non_aligned_targets(self):
        self.assertEqual(exeltgtpxy.calculate_tgt(True), 77.0)
        self.assertEqual(exeltgtpxy.calculate_tgt(False), 1.4)

        aligned_ce = {
            "pxy_entry": 1000, "symbol": "NIFTYCE", "exit": "BULL",
            "supertrend": "BULL", "atr": 500,
        }
        aligned_pe = {
            "pxy_entry": 1000, "symbol": "NIFTYPE", "exit": "BEAR",
            "supertrend": "BEAR", "atr": 0,
        }
        non_aligned_ce = {**aligned_ce, "exit": "BEAR"}
        side_ce = {**aligned_ce, "exit": "SIDE"}
        side_pe = {**aligned_pe, "exit": "SIDE"}
        supertrend_side_with_directional_exit = {
            **aligned_ce, "supertrend": "SIDE",
        }
        router_signals_disagree = {**aligned_ce, "exit": "BEAR"}
        neutral_supertrend_ignores_bull_exit = {
            **aligned_ce, "supertrend": "SIDE",
        }
        neutral_supertrend_ignores_bear_exit = {
            **aligned_pe, "supertrend": "SIDE",
        }

        self.assertEqual(exeltgtpxy.target_price(aligned_ce), 1770.0)
        self.assertEqual(exeltgtpxy.target_price(aligned_pe), 1770.0)
        self.assertEqual(exeltgtpxy.target_price(non_aligned_ce), 1014.0)
        self.assertEqual(exeltgtpxy.target_price(side_ce), 1014.0)
        self.assertEqual(exeltgtpxy.target_price(side_pe), 1014.0)
        self.assertEqual(exeltgtpxy.target_price(supertrend_side_with_directional_exit), 1014.0)
        self.assertEqual(exeltgtpxy.target_price(router_signals_disagree), 1014.0)
        self.assertEqual(exeltgtpxy.target_price(neutral_supertrend_ignores_bull_exit), 1014.0)
        self.assertEqual(exeltgtpxy.target_price(neutral_supertrend_ignores_bear_exit), 1014.0)

    def test_direx_uses_direction_for_heavier_side_and_exit_for_lighter_side(self):
        ce_heavy = {
            "pxy_entry": 1000, "symbol": "NIFTYCE", "exit": "BEAR",
            "direction": "UP", "supertrend": "BULL",
        }
        pe_light = {
            "pxy_entry": 1000, "symbol": "NIFTYPE", "exit": "BEAR",
            "direction": "UP", "supertrend": "BEAR",
        }
        ce_light = {**ce_heavy, "direction": "DOWN"}
        pe_heavy = {**pe_light, "exit": "BULL", "direction": "DOWN"}
        ce_heavy_direction_flip = {**ce_heavy, "exit": "BULL", "direction": "DOWN"}
        pe_heavy_direction_flip = {**pe_light, "direction": "UP"}

        self.assertEqual(exeltgtpxy.target_price(ce_heavy, 2000, 1000), 1770.0)
        self.assertEqual(exeltgtpxy.target_price(pe_light, 2000, 1000), 1770.0)
        self.assertEqual(exeltgtpxy.target_price(ce_light, 1000, 2000), 1014.0)
        self.assertEqual(exeltgtpxy.target_price(pe_heavy, 1000, 2000), 1770.0)
        self.assertEqual(exeltgtpxy.target_price(ce_heavy_direction_flip, 2000, 1000), 1014.0)
        self.assertEqual(exeltgtpxy.target_price(pe_heavy_direction_flip, 1000, 2000), 1014.0)

        with patch.object(exeltgtpxy, "TARGET_MODE", "RGLR"):
            self.assertEqual(exeltgtpxy.target_price(ce_heavy, 2000, 1000), 1014.0)

    def test_direx_ties_and_unavailable_direction_fall_back_to_exit(self):
        row = {
            "pxy_entry": 1000, "symbol": "NIFTYCE", "exit": "BULL",
            "direction": "SIDE", "supertrend": "BULL",
        }
        self.assertEqual(exeltgtpxy.target_price(row, 1000, 1000), 1770.0)
        self.assertEqual(exeltgtpxy.target_price(row, 2000, 1000), 1770.0)

    def test_dirgt_lighter_side_uses_exit_when_supertrend_is_side(self):
        aligned_lighter_ce = {
            "pxy_entry": 1000, "symbol": "NIFTYCE", "exit": "BULL",
            "direction": "DOWN", "supertrend": "SIDE",
        }
        nonaligned_lighter_pe = {
            "pxy_entry": 1000, "symbol": "NIFTYPE", "exit": "BULL",
            "direction": "UP", "supertrend": "SIDE",
        }
        heavier_ce = {**aligned_lighter_ce, "direction": "SIDE"}

        self.assertEqual(
            exeltgtpxy.target_price(aligned_lighter_ce, 1000, 2000),
            1770.0,
        )
        self.assertEqual(
            exeltgtpxy.target_price(nonaligned_lighter_pe, 2000, 1000),
            1014.0,
        )
        self.assertEqual(exeltgtpxy.target_price(heavier_ce, 2000, 1000), 1014.0)

    def test_direx_averaging_uses_direction_for_the_lighter_side(self):
        ce_aligned, pe_aligned = exeavxpxy.averaging_alignment_signals(
            "BULL", "UP", ce_investment=1000, pe_investment=2000,
            sma_status="BULL",
        )
        self.assertTrue(ce_aligned)
        self.assertFalse(pe_aligned)

        ce_aligned, pe_aligned = exeavxpxy.averaging_alignment_signals(
            "BEAR", "DOWN", ce_investment=2000, pe_investment=1000,
            sma_status="BEAR",
        )
        self.assertFalse(ce_aligned)
        self.assertTrue(pe_aligned)

        with patch.object(exeavxpxy, "EXETGTPXY_MODE", "RGLR"):
            ce_aligned, pe_aligned = exeavxpxy.averaging_alignment_signals(
                "BEAR", "UP", ce_investment=1000, pe_investment=2000,
                sma_status="BEAR",
            )
        self.assertFalse(ce_aligned)
        self.assertTrue(pe_aligned)

    def test_tsma_counter_trend_allows_averaging_with_doubled_loss_threshold(self):
        ce_aligned, pe_aligned = exeavxpxy.averaging_alignment_signals(
            "BULL", "UP", 1000, 1000, sma_status="BEAR"
        )
        self.assertTrue(ce_aligned)
        self.assertFalse(pe_aligned)

        ce_aligned, pe_aligned = exeavxpxy.averaging_alignment_signals(
            "BEAR", "DOWN", 1000, 1000, sma_status="BULL"
        )
        self.assertFalse(ce_aligned)
        self.assertTrue(pe_aligned)

        self.assertEqual(EXEAVXPXY_COUNTER_TREND_LOSS_MULTIPLIER, 2.0)
        self.assertEqual(
            exeavxpxy.counter_trend_averaging_thresholds(-5.0, -7.0, "BEAR"),
            (-10.0, -7.0),
        )
        self.assertEqual(
            exeavxpxy.counter_trend_averaging_thresholds(-5.0, -7.0, "BULL"),
            (-5.0, -14.0),
        )
        self.assertEqual(
            exeavxpxy.counter_trend_averaging_thresholds(-5.0, -7.0, "NA"),
            (-5.0, -7.0),
        )
        self.assertEqual(
            exeavxpxy.counter_trend_averaging_thresholds(-77.0, -20.0, "BEAR"),
            (-154.0, -20.0),
        )

        for unknown in ("NA", "NONE", ""):
            with self.subTest(sma_status=unknown):
                self.assertEqual(
                    exeavxpxy.averaging_alignment_signals(
                        "BULL", "UP", 1000, 1000, sma_status=unknown
                    ),
                    (False, False),
                )

    def test_lgt_uses_base_twenty_and_reduces_lesser_side_by_two_point_eight(self):
        self.assertEqual(exeltgtpxy.calculate_lgt(1000.0, 4000.0, is_ce=True), -1.4)
        self.assertEqual(exeltgtpxy.calculate_lgt(2000.0, 4000.0, is_ce=True), -2.2)
        self.assertEqual(exeltgtpxy.calculate_lgt(1000.0, 1000.0, is_ce=True), -20.0)
        self.assertEqual(exeltgtpxy.calculate_lgt(2000.0, 1000.0, is_ce=True), -77.0)
        self.assertEqual(exeltgtpxy.calculate_lgt(3000.0, 1000.0, is_ce=True), -77.0)
        self.assertEqual(exeltgtpxy.calculate_lgt(1000.0, 4000.0, is_ce=False), -77.0)

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
