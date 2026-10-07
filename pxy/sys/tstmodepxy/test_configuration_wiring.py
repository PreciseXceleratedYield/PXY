import re
import sys
import unittest
from contextlib import redirect_stdout
from datetime import date, timedelta
from io import StringIO
from pathlib import Path
from unittest.mock import patch

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
import sysentrpxy
import runniftypxy
from syscnfgpxy import (
    SYSCNFGPXY_ACTION_COOLDOWN_SECONDS,
    SYSCNFGPXY_TIMEZONE,
    SYSDTAFPXY_FIXED_BRICK_SIZE,
    SYSENTRPXY_SIGNAL_MODE,
    EXEAMSPXY_MAX_INVESTMENT,
    EXECBUYPXY_ENTRY_KEY_COLUMN,
)
from sysdtafpxy import apply_ohlc_transformation
from sysdecisionpxy import averaging_trigger_sides
import syskatrpxy


class ConfigurationWiringTests(unittest.TestCase):
    def test_entry_router_defaults_to_configured_sts_mode(self):
        self.assertEqual(SYSENTRPXY_SIGNAL_MODE, "STS")
        self.assertEqual(sysentrpxy.get_entry_signal.__defaults__[-1], "STS")

    def test_mkt_entry_router_bypasses_supertrend(self):
        frame = pd.DataFrame({"Close": [1]})
        with (
            patch.object(sysentrpxy, "get_signal", return_value=("BEAR", None)),
            patch.object(sysentrpxy, "calculate_supertrend") as supertrend,
        ):
            self.assertEqual(
                sysentrpxy.get_entry_signal(frame, mode="MKT"),
                ("SELL", "BEAR"),
            )

        supertrend.assert_not_called()

    def test_sts_entry_router_uses_supertrend_matrix(self):
        frame = pd.DataFrame({"Close": [1]})
        with (
            patch.object(sysentrpxy, "get_signal", return_value=("BEAR", None)),
            patch.object(
                sysentrpxy,
                "calculate_supertrend",
                return_value=pd.DataFrame({"ST_Trend": ["BULL"]}),
            ),
        ):
            self.assertEqual(
                sysentrpxy.get_entry_signal(frame, mode="STS"),
                ("BUY", "BULL"),
            )

    def test_entry_router_rejects_old_or_unknown_mode_names(self):
        with self.assertRaisesRegex(ValueError, "STS.*MKT"):
            sysentrpxy.get_entry_signal(pd.DataFrame({"Close": [1]}), mode="ST")

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

    def test_lgt_uses_base_fourteen_piecewise_investment_ratio(self):
        self.assertEqual(exeltgtpxy.calculate_lgt(1000.0, 4000.0, is_ce=True), -0.88)
        self.assertEqual(exeltgtpxy.calculate_lgt(1000.0, 2000.0, is_ce=True), -3.5)
        self.assertEqual(exeltgtpxy.calculate_lgt(1000.0, 1000.0, is_ce=True), -14.0)
        self.assertEqual(exeltgtpxy.calculate_lgt(2000.0, 1000.0, is_ce=True), -56.0)
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
