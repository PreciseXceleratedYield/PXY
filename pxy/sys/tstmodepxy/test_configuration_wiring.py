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
    EXEAVXPXY_ALIGNED_LGT_MULTIPLIER,
    EXEAVXPXY_NOT_ALIGNED_LGT_MULTIPLIER,
)
from sysdtafpxy import apply_ohlc_transformation
from sysdecisionpxy import scale_lgt_threshold
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

    def test_dynamic_non_aligned_target_uses_configured_percentage(self):
        with patch.object(exeltgtpxy, "STATIC_NOT_ALIGNED_PCT", 2.3):
            target = exeltgtpxy.calculate_tgt(
                5.0, 100.0, 100.0, 1, 1, True, False
            )

        self.assertEqual(target, 2.3)

    def test_dynamic_target_price_uses_calculated_aligned_target_and_non_aligned_floor(self):
        aligned = {
            "pxy_entry": 1000,
            "symbol": "NIFTYCE",
            "exit": "BULL",
            "atr": 5,
        }
        not_aligned = {**aligned, "exit": "BEAR"}

        with (
            patch.object(exeltgtpxy, "TGT_MODE", "DYNAMIC"),
            patch.object(exeltgtpxy, "MIN_ATR_VALUE", 5.0),
            patch.object(exeltgtpxy, "MIN_TARGET_PCT", 1.4),
            patch.object(exeltgtpxy, "MAX_TARGET_CAP", 77.0),
            patch.object(exeltgtpxy, "STATIC_NOT_ALIGNED_PCT", 1.4),
        ):
            aligned_target = exeltgtpxy.target_price(
                aligned, ce_investment=100, pe_investment=200
            )
            not_aligned_target = exeltgtpxy.target_price(
                not_aligned, ce_investment=100, pe_investment=200
            )

        self.assertEqual(aligned_target, 1500.0)
        self.assertEqual(not_aligned_target, 1014.0)

    def test_target_uses_original_alignment_rules(self):
        aligned = {
            "pxy_entry": 1000, "symbol": "NIFTYCE", "exit": "BULL", "atr": 5,
        }
        with (
            patch.object(exeltgtpxy, "TGT_MODE", "DYNAMIC"),
            patch.object(exeltgtpxy, "MIN_ATR_VALUE", 5.0),
            patch.object(exeltgtpxy, "MIN_TARGET_PCT", 1.4),
            patch.object(exeltgtpxy, "MAX_TARGET_CAP", 77.0),
        ):
            target = exeltgtpxy.target_price(
                aligned, ce_investment=200, pe_investment=100
            )

        self.assertEqual(target, 1162.5)

    def test_static_target_uses_alignment_not_investment_imbalance(self):
        aligned = {
            "pxy_entry": 1000, "symbol": "NIFTYCE", "exit": "BULL", "atr": 5,
        }
        not_aligned = {**aligned, "exit": "BEAR"}
        with (
            patch.object(exeltgtpxy, "TGT_MODE", "STATIC"),
            patch.object(exeltgtpxy, "MIN_TARGET_PCT", 1.4),
            patch.object(exeltgtpxy, "STATIC_NOT_ALIGNED_PCT", 1.4),
            patch.object(exeltgtpxy, "STATIC_ALIGNED_PCT", 99.0),
        ):
            aligned_target = exeltgtpxy.target_price(
                aligned, ce_investment=200, pe_investment=100
            )
            not_aligned_target = exeltgtpxy.target_price(
                not_aligned, ce_investment=200, pe_investment=100
            )

        self.assertEqual(aligned_target, 1990.0)
        self.assertEqual(not_aligned_target, 1014.0)

    def test_lgt_alignment_multipliers_match_requested_policy(self):
        self.assertEqual(EXEAVXPXY_ALIGNED_LGT_MULTIPLIER, 0.5)
        self.assertEqual(EXEAVXPXY_NOT_ALIGNED_LGT_MULTIPLIER, 2.0)
        self.assertEqual(
            scale_lgt_threshold(
                -10.0,
                True,
                EXEAVXPXY_ALIGNED_LGT_MULTIPLIER,
                EXEAVXPXY_NOT_ALIGNED_LGT_MULTIPLIER,
            ),
            -5.0,
        )
        self.assertEqual(
            scale_lgt_threshold(
                -10.0,
                False,
                EXEAVXPXY_ALIGNED_LGT_MULTIPLIER,
                EXEAVXPXY_NOT_ALIGNED_LGT_MULTIPLIER,
            ),
            -20.0,
        )

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
