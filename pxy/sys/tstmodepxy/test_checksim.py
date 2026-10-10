import sys
import unittest
from pathlib import Path
from unittest.mock import patch

SYS_DIR = Path(__file__).resolve().parents[1]
if str(SYS_DIR) not in sys.path:
    sys.path.insert(0, str(SYS_DIR))

from tstmodepxy import checksim


class CheckSimTests(unittest.TestCase):
    def test_chk_runner_invokes_only_isolated_test_suite(self):
        with patch.object(checksim, "_run_stage", return_value=0) as run_stage:
            self.assertEqual(checksim.main(), 0)

        run_stage.assert_called_once()
        label, command, run_mode = run_stage.call_args.args
        self.assertEqual(label, "CHK test suite")
        self.assertEqual(command[1:4], ["-m", "unittest", "discover"])
        self.assertEqual(run_mode, "CHK")

    def test_chk_runner_returns_test_failure_without_starting_sim(self):
        with patch.object(checksim, "_run_stage", return_value=1) as run_stage:
            self.assertEqual(checksim.main(), 1)

        run_stage.assert_called_once()
