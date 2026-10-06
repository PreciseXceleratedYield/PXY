import unittest
import sys
from pathlib import Path
from unittest.mock import patch

SYS_DIR = Path(__file__).resolve().parents[1]
EXE_DIR = SYS_DIR / "exe"
if str(SYS_DIR) not in sys.path:
    sys.path.insert(0, str(SYS_DIR))
if str(EXE_DIR) not in sys.path:
    sys.path.insert(0, str(EXE_DIR))

import exeltgtpxy
from syscnfgpxy import SYSCNFGPXY_TIMEZONE, SYSDTAFPXY_TIMEZONE


class ConfigurationWiringTests(unittest.TestCase):
    def test_dynamic_non_aligned_target_uses_configured_percentage(self):
        with patch.object(exeltgtpxy, "STATIC_NOT_ALIGNED_PCT", 2.3):
            target = exeltgtpxy.calculate_tgt(
                5.0, 100.0, 100.0, 1, 1, True, False
            )

        self.assertEqual(target, 2.3)

    def test_data_timezone_is_derived_from_shared_timezone(self):
        self.assertEqual(SYSDTAFPXY_TIMEZONE, str(SYSCNFGPXY_TIMEZONE))


if __name__ == "__main__":
    unittest.main()
