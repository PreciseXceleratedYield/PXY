import sys
import tempfile
import unittest
from datetime import time
from pathlib import Path
from unittest.mock import patch

SYS_DIR = Path(__file__).resolve().parents[1]
if str(SYS_DIR) not in sys.path:
    sys.path.insert(0, str(SYS_DIR))

RUN_DIR = SYS_DIR / "exe" / "run"
if str(RUN_DIR) not in sys.path:
    sys.path.insert(0, str(RUN_DIR))

from runexmtpxy import compute_stop, midday_risk_activation_due
import runexstpxy


class MiddayRiskControlTests(unittest.TestCase):
    def test_fixed_loss_and_target_thresholds_scale_by_active_row_count(self):
        self.assertEqual(compute_stop(-400, 0, active_count=5), (0.0, -400.0, True))
        self.assertEqual(compute_stop(-399, 0, active_count=5), (0.0, -400.0, False))
        self.assertEqual(compute_stop(350, 0, active_count=5), (350.0, -400.0, False))
        self.assertEqual(compute_stop(400, 0, active_count=5), (400.0, -400.0, True))

    def test_peak_does_not_change_fixed_loss_or_target_thresholds(self):
        one_row = compute_stop(1200, 1500, active_count=1)
        five_rows = compute_stop(1200, 1500, active_count=5)

        self.assertEqual(one_row, (1500.0, -2000.0, False))
        self.assertEqual(five_rows, (1500.0, -400.0, True))

    def test_positive_target_is_based_on_current_pnl_not_peak(self):
        self.assertEqual(compute_stop(399, 0, active_count=5), (350.0, -400.0, False))
        self.assertEqual(compute_stop(400, 0, active_count=5), (400.0, -400.0, True))

    def test_default_and_zero_active_rows_preserve_unscaled_thresholds(self):
        self.assertEqual(compute_stop(-2000, 0), (-0.0, -2000.0, True))
        self.assertEqual(
            compute_stop(-2000, 0, active_count=0),
            compute_stop(-2000, 0, active_count=1),
        )

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
