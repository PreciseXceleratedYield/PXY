import sys
import unittest
from pathlib import Path
from unittest.mock import patch

SYS_DIR = Path(__file__).resolve().parents[1]
EXE_DIR = SYS_DIR / "exe"
for path in (SYS_DIR, EXE_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import exepxy


class EngineRuntimeTests(unittest.TestCase):
    def test_production_cycle_runs_exit_entry_then_averaging(self):
        calls = []

        def record_script(script, timeout=None):
            calls.append((Path(script).name, timeout))

        with patch.object(exepxy, "safe_run", side_effect=record_script), patch.object(
            exepxy, "fancy_pause"
        ) as pause:
            exepxy.run_market_cycle()

        self.assertEqual(
            calls,
            [
                ("exeexitpxy.py", exepxy.EXEPXYPXY_PIPE_TIMEOUT_SECONDS),
                ("exeentrpxy.py", exepxy.EXEPXYPXY_PIPE_TIMEOUT_SECONDS),
                ("exeavgpxy.py", exepxy.EXEPXYPXY_PIPE_TIMEOUT_SECONDS),
            ],
        )
        pause.assert_called_once_with(exepxy.SYSCNFGPXY_ACTION_COOLDOWN_SECONDS)
