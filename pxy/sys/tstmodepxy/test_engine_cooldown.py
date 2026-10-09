import sys
import tempfile
import unittest
from datetime import time
from pathlib import Path
from unittest.mock import patch

import pandas as pd

SYS_DIR = Path(__file__).resolve().parents[1]
EXE_DIR = SYS_DIR / "exe"
RUN_DIR = EXE_DIR / "run"
for path in (SYS_DIR, EXE_DIR, RUN_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import execoolpxy
import sysentrpxy
from syscnfgpxy import EXESQRPXY_POST_EXIT_COOLDOWN_SECONDS


class EngineCooldownTests(unittest.TestCase):
    def test_squareoff_cooldown_persists_and_expires(self):
        with tempfile.TemporaryDirectory(prefix="pxy-engine-cooldown-") as temp:
            marker = Path(temp) / "cooldown.json"
            with patch.object(execoolpxy, "COOLDOWN_FILE", marker), patch.object(
                execoolpxy, "WEB_DIR", Path(temp)
            ):
                execoolpxy.start_cooldown(now=1000)
                self.assertEqual(
                    execoolpxy.cooldown_remaining(now=1000),
                    EXESQRPXY_POST_EXIT_COOLDOWN_SECONDS,
                )
                self.assertEqual(execoolpxy.cooldown_remaining(now=1005), 1)
                self.assertEqual(execoolpxy.cooldown_remaining(now=1006), 0)

    def test_signal_router_returns_none_during_cooldown(self):
        with tempfile.TemporaryDirectory(prefix="pxy-signal-cooldown-") as temp:
            marker = Path(temp) / "cooldown.json"
            frame = pd.DataFrame({"Close": [1]})
            with (
                patch.object(execoolpxy, "COOLDOWN_FILE", marker),
                patch.object(execoolpxy, "WEB_DIR", Path(temp)),
                patch.object(sysentrpxy, "cooldown_remaining", side_effect=execoolpxy.cooldown_remaining),
                patch.object(sysentrpxy, "calculate_supertrend") as calculate_supertrend,
                patch.object(sysentrpxy, "detect_raw_direction") as detect_raw_direction,
            ):
                execoolpxy.start_cooldown()
                self.assertEqual(
                    sysentrpxy.get_entry_signal(frame),
                    ("NONE", "NONE"),
                )
            calculate_supertrend.assert_not_called()
            detect_raw_direction.assert_not_called()

    def test_signal_router_uses_normal_signal_after_cooldown(self):
        with (
            patch.object(sysentrpxy, "cooldown_remaining", return_value=0),
            patch.object(sysentrpxy, "SYSENTRPXY_SIGNAL_MODE", "STS"),
            patch.object(
                sysentrpxy,
                "calculate_supertrend",
                return_value=pd.DataFrame({"ST_Trend": ["BULL"]}),
            ),
        ):
            self.assertEqual(
                sysentrpxy.get_entry_signal(
                    pd.DataFrame({"Close": [1]}),
                    current_time=time(10, 0),
                ),
                ("BUY", "BULL"),
            )


if __name__ == "__main__":
    unittest.main()
