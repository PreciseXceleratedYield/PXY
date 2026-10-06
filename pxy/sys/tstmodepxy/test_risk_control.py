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

from runexmtpxy import midday_risk_activation_due
import runexstpxy


class MiddayRiskControlTests(unittest.TestCase):
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
                    0.0, 0.0, -2000.0, 1250.0, risk_control_activated=True
                )
                state = runexstpxy.load_session_state()

        self.assertTrue(state["risk_control_activated"])
        self.assertEqual(state["pnl_offset"], 1250.0)


if __name__ == "__main__":
    unittest.main()
