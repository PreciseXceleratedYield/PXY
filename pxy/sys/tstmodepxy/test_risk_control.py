import sys
import tempfile
import unittest
from datetime import time
from pathlib import Path
from unittest.mock import patch

import pandas as pd

SYS_DIR = Path(__file__).resolve().parents[1]
if str(SYS_DIR) not in sys.path:
    sys.path.insert(0, str(SYS_DIR))

RUN_DIR = SYS_DIR / "exe" / "run"
if str(RUN_DIR) not in sys.path:
    sys.path.insert(0, str(RUN_DIR))

from runexmtpxy import compute_stop, compute_totals, midday_risk_activation_due
from syscnfgpxy import (
    RUNEXACPXY_CNTRLRSKBAR,
    RUNEXACPXY_CNTRLRSKBAR_ACTIVATION_TIME,
    RUNEXACPXY_RISK_MODE,
    RUNEXACPXY_STOP_SQUAREOFF_ENABLED,
    RUNEXACPXY_TARGET_SQUAREOFF_ENABLED,
    _risk_candle_activation_settings,
)
import runexstpxy


class MiddayRiskControlTests(unittest.TestCase):
    def test_default_risk_control_has_no_midday_activation_dependency(self):
        self.assertEqual(RUNEXACPXY_CNTRLRSKBAR, "NO")
        self.assertIsNone(RUNEXACPXY_CNTRLRSKBAR_ACTIVATION_TIME)
        self.assertEqual(RUNEXACPXY_RISK_MODE, "STATIC")

    def test_stop_squareoff_is_disabled_but_static_target_still_triggers(self):
        self.assertFalse(RUNEXACPXY_STOP_SQUAREOFF_ENABLED)
        self.assertTrue(RUNEXACPXY_TARGET_SQUAREOFF_ENABLED)
        self.assertFalse(compute_stop(-2000, 0)[2])
        self.assertTrue(compute_stop(2000, 0)[2])

        with patch("runexmtpxy.STOP_SQUAREOFF_ENABLED", True):
            self.assertTrue(compute_stop(-2000, 0)[2])

        with patch("runexmtpxy.TARGET_SQUAREOFF_ENABLED", False):
            self.assertFalse(compute_stop(2000, 0)[2])

    def test_peak_mode_uses_original_midday_activation_gate(self):
        self.assertEqual(
            _risk_candle_activation_settings("PEAK"),
            ("YES", time(13, 15)),
        )
        self.assertEqual(
            _risk_candle_activation_settings("STATIC"),
            ("NO", None),
        )

    def test_static_risk_uses_side_imbalance_factor_for_loss_and_target(self):
        with (
            patch("runexmtpxy.STOP_SQUAREOFF_ENABLED", True),
            patch("runexmtpxy.TARGET_SQUAREOFF_ENABLED", False),
        ):
            self.assertEqual(compute_stop(-3999, 0, imbalance_factor=2), (0.0, -4000.0, False))
            self.assertEqual(compute_stop(-4000, 0, imbalance_factor=2), (0.0, -4000.0, True))
            self.assertEqual(compute_stop(350, 0, imbalance_factor=2), (350.0, -4000.0, False))
            self.assertEqual(compute_stop(1000, 0, imbalance_factor=2), (1000.0, -4000.0, False))

    def test_risk_factor_is_count_difference_plus_one(self):
        balanced = compute_totals(
            pd.DataFrame([{"Symbol": "NIFTY-CE"}, {"Symbol": "NIFTY-PE"}]),
            pd.DataFrame(),
        )
        two_to_one = compute_totals(
            pd.DataFrame([
                {"Symbol": "NIFTY-CE"},
                {"Symbol": "NIFTY-CE"},
                {"Symbol": "NIFTY-PE"},
            ]),
            pd.DataFrame(),
        )
        zero_to_one = compute_totals(
            pd.DataFrame([{"Symbol": "NIFTY-PE"}]),
            pd.DataFrame(),
        )
        three_to_one = compute_totals(
            pd.DataFrame([
                {"Symbol": "NIFTY-CE"},
                {"Symbol": "NIFTY-CE"},
                {"Symbol": "NIFTY-CE"},
                {"Symbol": "NIFTY-PE"},
            ]),
            pd.DataFrame(),
        )

        self.assertEqual((balanced["ce_rows"], balanced["pe_rows"]), (1, 1))
        self.assertEqual(balanced["imbalance_factor"], 1)
        self.assertEqual((two_to_one["ce_rows"], two_to_one["pe_rows"]), (2, 1))
        self.assertEqual(two_to_one["imbalance_factor"], 2)
        self.assertEqual((zero_to_one["ce_rows"], zero_to_one["pe_rows"]), (0, 1))
        self.assertEqual(zero_to_one["imbalance_factor"], 2)
        self.assertEqual((three_to_one["ce_rows"], three_to_one["pe_rows"]), (3, 1))
        self.assertEqual(three_to_one["imbalance_factor"], 3)

    def test_peak_does_not_change_static_thresholds(self):
        with patch("runexmtpxy.TARGET_SQUAREOFF_ENABLED", True):
            one_row = compute_stop(1200, 1500, imbalance_factor=1)
            five_rows = compute_stop(1200, 1500, imbalance_factor=5)

        self.assertEqual(one_row, (1500.0, -2000.0, False))
        self.assertEqual(five_rows, (1500.0, -10000.0, True))

    def test_positive_target_is_based_on_current_pnl_not_peak(self):
        self.assertEqual(compute_stop(399, 0, imbalance_factor=2), (350.0, -4000.0, False))
        self.assertEqual(compute_stop(400, 0, imbalance_factor=2), (400.0, -4000.0, False))

    def test_default_and_zero_factor_preserve_unscaled_thresholds(self):
        self.assertEqual(compute_stop(-2000, 0), (-0.0, -2000.0, False))
        self.assertEqual(
            compute_stop(-2000, 0, imbalance_factor=0),
            (-0.0, -2000.0, False),
        )

    def test_peak_mode_restores_original_peak_trailing_stop(self):
        from runexmtpxy import PEAK_CEILING

        with patch("runexmtpxy.RISK_MODE", "PEAK"):
            self.assertEqual(compute_stop(-1799, 100), (100.0, -1800.0, False))
            self.assertEqual(compute_stop(-1800, 100), (100.0, -1800.0, False))
            self.assertEqual(compute_stop(PEAK_CEILING, 0), (PEAK_CEILING, 2000.0, True))

        with (
            patch("runexmtpxy.RISK_MODE", "PEAK"),
            patch("runexmtpxy.STOP_SQUAREOFF_ENABLED", True),
            patch("runexmtpxy.TARGET_SQUAREOFF_ENABLED", False),
        ):
            self.assertTrue(compute_stop(-1800, 100)[2])

    def test_yes_activates_at_or_after_1315_ist(self):
        activation_time = time(13, 15)
        self.assertFalse(
            midday_risk_activation_due(True, False, time(13, 14, 59), activation_time)
        )
        self.assertTrue(
            midday_risk_activation_due(True, False, time(13, 15), activation_time)
        )
        self.assertTrue(
            midday_risk_activation_due(True, False, time(13, 16), activation_time)
        )

    def test_no_and_already_activated_do_not_take_a_new_baseline(self):
        self.assertFalse(
            midday_risk_activation_due(False, False, time(14, 0), None)
        )
        self.assertFalse(
            midday_risk_activation_due(True, False, time(14, 0), None)
        )
        self.assertFalse(
            midday_risk_activation_due(True, True, time(14, 0), time(13, 15))
        )

    def test_activation_state_persists_across_ledger_restarts(self):
        with tempfile.TemporaryDirectory(prefix="pxy-risk-state-test-") as temp:
            state_path = Path(temp) / "risk.json"
            with patch.object(runexstpxy, "RENKO_STATE_FILE", str(state_path)):
                runexstpxy.save_session_state(
                    0.0, 0.0, -2000.0, 1250.0, risk_control_activated=True,
                    target_exit_line=400.0,
                )
                state = runexstpxy.load_session_state()

        self.assertTrue(state["risk_control_activated"])
        self.assertEqual(state["pnl_offset"], 1250.0)
        self.assertEqual(state["active_target_line"], 400.0)


if __name__ == "__main__":
    unittest.main()
