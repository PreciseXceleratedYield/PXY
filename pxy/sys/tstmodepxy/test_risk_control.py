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

from runexmtpxy import (
    compute_stop,
    compute_stop_conditions,
    compute_totals,
    large_invested_side_aligned,
    midday_risk_activation_due,
    target_ceiling,
)
from syscnfgpxy import (
    RUNEXACPXY_CNTRLRSKBAR,
    RUNEXACPXY_CNTRLRSKBAR_ACTIVATION_TIME,
    RUNEXACPXY_STOP_SQUAREOFF_ENABLED,
    RUNEXACPXY_TARGET_SQUAREOFF_ENABLED,
)
import runexstpxy


class MiddayRiskControlTests(unittest.TestCase):
    def test_peak_risk_control_activates_at_1315(self):
        self.assertEqual(RUNEXACPXY_CNTRLRSKBAR, "YES")
        self.assertEqual(RUNEXACPXY_CNTRLRSKBAR_ACTIVATION_TIME, time(13, 15))

    def test_stop_squareoff_is_disabled_but_peak_target_still_triggers(self):
        self.assertFalse(RUNEXACPXY_STOP_SQUAREOFF_ENABLED)
        self.assertTrue(RUNEXACPXY_TARGET_SQUAREOFF_ENABLED)
        self.assertFalse(compute_stop(-2000, 0)[2])
        self.assertTrue(compute_stop(2000, 0)[2])

        with patch("runexmtpxy.STOP_SQUAREOFF_ENABLED", True):
            self.assertTrue(compute_stop(-2000, 0)[2])

        with patch("runexmtpxy.TARGET_SQUAREOFF_ENABLED", False):
            self.assertFalse(compute_stop(2000, 0)[2])

    def test_peak_trailing_stop_uses_historical_peak(self):
        with patch("runexmtpxy.TARGET_SQUAREOFF_ENABLED", True):
            peak_state = compute_stop(1200, 1500)

        self.assertEqual(peak_state, (1500.0, 1000.0, False))

    def test_positive_target_is_based_on_current_pnl_not_peak(self):
        self.assertEqual(compute_stop(399, 0), (350.0, -1300.0, False))
        self.assertEqual(compute_stop(400, 0), (400.0, -1200.0, False))

    def test_peak_stop_uses_unscaled_loss_floor(self):
        self.assertEqual(compute_stop(-2000, 0), (-0.0, -2000.0, False))

    def test_peak_trailing_stop_and_target(self):
        from runexmtpxy import PEAK_CEILING

        self.assertEqual(compute_stop(-1799, 100), (100.0, -1800.0, False))
        self.assertEqual(compute_stop(-1800, 100), (100.0, -1800.0, False))
        self.assertEqual(compute_stop(PEAK_CEILING, 0), (PEAK_CEILING, 2000.0, True))

        with (
            patch("runexmtpxy.STOP_SQUAREOFF_ENABLED", True),
            patch("runexmtpxy.TARGET_SQUAREOFF_ENABLED", False),
        ):
            self.assertTrue(compute_stop(-1800, 100)[2])

    def test_risk_target_scales_by_active_open_rung_count(self):
        self.assertEqual(target_ceiling(1), 1000.0)
        self.assertEqual(target_ceiling(2), 2000.0)
        self.assertEqual(target_ceiling(3), 3000.0)
        self.assertEqual(target_ceiling(0), 1000.0)

        self.assertFalse(compute_stop_conditions(1000, 0, active_count=2)[3])
        self.assertTrue(compute_stop_conditions(1000, 0, active_count=1)[3])
        self.assertTrue(compute_stop_conditions(3000, 0, active_count=3)[3])
        self.assertEqual(
            {
                compute_stop_conditions(0, 0, active_count=count)[1]
                for count in (1, 2, 3)
            },
            {-2000.0},
        )

    def test_target_suppression_requires_higher_invested_side_to_match_signal(self):
        ce_heavy = pd.DataFrame([
            {"Symbol": "NIFTY-CE", "Qty": 75, "SELL_PRC": 100},
            {"Symbol": "NIFTY-PE", "Qty": 75, "SELL_PRC": 50},
        ])
        pe_heavy = ce_heavy.assign(SELL_PRC=[50, 100])
        balanced = ce_heavy.assign(SELL_PRC=[100, 100])

        self.assertTrue(large_invested_side_aligned(ce_heavy, "UP"))
        self.assertFalse(large_invested_side_aligned(ce_heavy, "DOWN"))
        self.assertTrue(large_invested_side_aligned(pe_heavy, "DOWN"))
        self.assertFalse(large_invested_side_aligned(balanced, "UP"))
        self.assertFalse(large_invested_side_aligned(ce_heavy, "NONE"))

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
