import tempfile
import unittest
from pathlib import Path
import runpy
from unittest.mock import patch

import pxyconfigwebpxy as config_editor


class ConfigEditorTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config_path = Path(self.temp_dir.name) / "syscnfgpxy.py"
        self.original = (
            "from datetime import time as dt_time\n"
            "FLAG = True\n"
            "RUNNIFTYPXY_STRIKE_STEP = 2\n"
            "CLOCK = dt_time(9, 0)\n"
            "SYSDTAFPXY_SELECTED_MODE = '00'\n"
            "RUNEXMTPXY_INITIAL_LOSS_FLOOR = -1000\n"
            "RUNEXACPXY_RISK_MODE = 'STATIC'\n"
            "HOLIDAYS = ('one', 'two')\n"
            "SCRIPTS = {'CE': 'buy', 'PE': 'sell'}\n"
            "TOKEN_VALUE = 'must stay hidden'\n"
            "DERIVED_VALUE = RUNNIFTYPXY_STRIKE_STEP * 2\n"
            "def _risk_candle_activation_settings(risk_mode):\n"
            "    if risk_mode == 'PEAK':\n"
            "        return 'YES', dt_time(13, 15)\n"
            "    return 'NO', None\n"
            "RUNEXACPXY_CNTRLRSKBAR, RUNEXACPXY_CNTRLRSKBAR_ACTIVATION_TIME = (\n"
            "    _risk_candle_activation_settings(RUNEXACPXY_RISK_MODE)\n"
            ")\n"
            "if RUNEXMTPXY_INITIAL_LOSS_FLOOR < -2000:\n"
            "    raise ValueError('loss floor is out of range')\n"
        )
        self.config_path.write_text(self.original, encoding="utf-8")
        self.config_patch = patch.object(config_editor, "CONFIG_PATH", self.config_path)
        self.config_patch.start()

    def tearDown(self):
        self.config_patch.stop()
        self.temp_dir.cleanup()

    def test_read_marks_derived_and_sensitive_values_read_only(self):
        settings, _ = config_editor._metadata(self.original)
        by_name = {setting["key"]: setting for setting in settings}
        self.assertFalse(by_name["TOKEN_VALUE"]["editable"])
        self.assertEqual(by_name["TOKEN_VALUE"]["value"], "[redacted]")
        self.assertFalse(by_name["DERIVED_VALUE"]["editable"])

    def test_new_strike_settings_are_visible_and_can_be_added_to_older_config(self):
        settings, _ = config_editor._metadata(self.original)
        by_name = {setting["key"]: setting for setting in settings}
        self.assertEqual(by_name["EXEOTMPXY_STRIKE_MODE"]["value"], "ATM")
        self.assertEqual(by_name["EXEOTMPXY_STRIKE_MODE"]["options"], ["ATM", "OTMFIX", "OTMDYN"])
        result = config_editor._write({
            "EXEOTMPXY_STRIKE_MODE": "OTMDYN",
            "EXEOTMPXY_FIXED_DISTANCE": 100,
            "EXEOTMPXY_DYNAMIC_WEEKDAY_DISTANCES": [200, 150, 100, 50, 0],
        })
        self.assertEqual(result["updated"], [
            "EXEOTMPXY_DYNAMIC_WEEKDAY_DISTANCES",
            "EXEOTMPXY_FIXED_DISTANCE",
            "EXEOTMPXY_STRIKE_MODE",
        ])
        source = self.config_path.read_text(encoding="utf-8")
        self.assertIn("EXEOTMPXY_STRIKE_MODE = 'OTMDYN'", source)
        self.assertIn("EXEOTMPXY_FIXED_DISTANCE = 100", source)
        self.assertIn("EXEOTMPXY_DYNAMIC_WEEKDAY_DISTANCES = (200, 150, 100, 50, 0)", source)

    def test_risk_mode_is_selectable_and_saved_through_config_editor(self):
        settings, _ = config_editor._metadata(self.original)
        risk_mode = next(
            setting for setting in settings
            if setting["key"] == "RUNEXACPXY_RISK_MODE"
        )
        self.assertEqual(risk_mode["value"], "STATIC")
        self.assertEqual(risk_mode["options"], ["PEAK", "STATIC"])

        for mode, activation, activation_time in (
            ("PEAK", "YES", "13:15:00"),
            ("STATIC", "NO", None),
        ):
            config_editor._write({"RUNEXACPXY_RISK_MODE": mode})
            runtime_config = runpy.run_path(str(self.config_path))
            self.assertEqual(runtime_config["RUNEXACPXY_RISK_MODE"], mode)
            self.assertEqual(runtime_config["RUNEXACPXY_CNTRLRSKBAR"], activation)
            actual_time = runtime_config["RUNEXACPXY_CNTRLRSKBAR_ACTIVATION_TIME"]
            self.assertEqual(
                actual_time.isoformat() if actual_time else None,
                activation_time,
            )

        with self.assertRaisesRegex(ValueError, "listed choices"):
            config_editor._write({"RUNEXACPXY_RISK_MODE": "UNKNOWN"})

    def test_write_validates_creates_backup_and_preserves_file_mode(self):
        self.config_path.chmod(0o640)
        result = config_editor._write({
            "FLAG": False,
            "RUNNIFTYPXY_STRIKE_STEP": 4,
            "CLOCK": "10:15:30",
            "SYSDTAFPXY_SELECTED_MODE": "8",
        })
        self.assertEqual(result["updated"], ["CLOCK", "FLAG", "RUNNIFTYPXY_STRIKE_STEP", "SYSDTAFPXY_SELECTED_MODE"])
        backup = self.config_path.with_name(result["backup"])
        self.assertEqual(backup.read_text(encoding="utf-8"), self.original)
        self.assertEqual(self.config_path.stat().st_mode & 0o777, 0o640)
        source = self.config_path.read_text(encoding="utf-8")
        self.assertIn("FLAG = False", source)
        self.assertIn("RUNNIFTYPXY_STRIKE_STEP = 4", source)
        self.assertIn("CLOCK = dt_time(10, 15, 30, 0)", source)
        self.assertIn("SYSDTAFPXY_SELECTED_MODE = '8'", source)

    def test_invalid_types_choices_and_bounds_leave_config_untouched(self):
        for updates in (
            {"FLAG": "false"},
            {"RUNNIFTYPXY_STRIKE_STEP": -1},
            {"SYSDTAFPXY_SELECTED_MODE": "99"},
            {"UNKNOWN": 1},
        ):
            with self.subTest(updates=updates):
                with self.assertRaises(ValueError):
                    config_editor._write(updates)
                self.assertEqual(self.config_path.read_text(encoding="utf-8"), self.original)

    def test_invalid_candidate_does_not_replace_config(self):
        with self.assertRaisesRegex(ValueError, "loss floor is out of range"):
            config_editor._write({"RUNEXMTPXY_INITIAL_LOSS_FLOOR": -3000})
        self.assertEqual(self.config_path.read_text(encoding="utf-8"), self.original)
        self.assertEqual(list(self.config_path.parent.glob(".syscnfgpxy.*.tmp")), [])

    def test_structured_values_keep_their_shape_and_types(self):
        for value in (["one"], ["one", 2], {"CE": "buy"}):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    config_editor._write({"HOLIDAYS": value} if isinstance(value, list) else {"SCRIPTS": value})
                self.assertEqual(self.config_path.read_text(encoding="utf-8"), self.original)
        config_editor._write({"HOLIDAYS": ["three", "four"], "SCRIPTS": {"CE": "call", "PE": "put"}})
        text = self.config_path.read_text(encoding="utf-8")
        self.assertIn("HOLIDAYS = ('three', 'four')", text)
        self.assertIn("'CE': 'call'", text)


if __name__ == "__main__":
    unittest.main()
