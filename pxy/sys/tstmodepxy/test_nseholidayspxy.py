import json
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

SYS_DIR = Path(__file__).resolve().parents[1]
if str(SYS_DIR) not in sys.path:
    sys.path.insert(0, str(SYS_DIR))

import nseholidayspxy


class NseHolidayCalendarTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.cache_path = Path(self.temp_dir.name) / "holidays.json"
        self.memory_cache_patch = patch.dict(nseholidayspxy._MEMORY_CACHE, {}, clear=True)
        self.memory_cache_patch.start()
        self.cache_path_patch = patch.object(
            nseholidayspxy, "HOLIDAY_CACHE_PATH", self.cache_path
        )
        self.cache_path_patch.start()

    def tearDown(self):
        self.cache_path_patch.stop()
        self.memory_cache_patch.stop()
        self.temp_dir.cleanup()

    def test_fetches_and_caches_calendar_once_per_day(self):
        holidays = frozenset({date(2026, 10, 20)})
        with patch.object(nseholidayspxy, "_fetch_holidays", return_value=holidays) as fetch:
            first = nseholidayspxy.get_nse_fo_holidays(date(2026, 10, 12))
            second = nseholidayspxy.get_nse_fo_holidays(date(2026, 10, 12))

        self.assertEqual(first, holidays)
        self.assertEqual(second, holidays)
        fetch.assert_called_once_with()
        self.assertEqual(
            json.loads(self.cache_path.read_text(encoding="utf-8")),
            {"fetched_on": "2026-10-12", "holidays": ["2026-10-20"]},
        )

    def test_uses_same_day_disk_cache_without_refetching(self):
        holidays = frozenset({date(2026, 10, 20)})
        nseholidayspxy._write_cache(date(2026, 10, 12), holidays)
        with patch.object(nseholidayspxy, "_fetch_holidays") as fetch:
            result = nseholidayspxy.get_nse_fo_holidays(date(2026, 10, 12))

        self.assertEqual(result, holidays)
        fetch.assert_not_called()

    def test_refreshes_stale_cache_and_uses_last_calendar_if_refresh_fails(self):
        nseholidayspxy._write_cache(
            date(2026, 10, 11), frozenset({date(2026, 10, 20)})
        )
        with patch.object(
            nseholidayspxy, "_fetch_holidays", side_effect=OSError("offline")
        ) as fetch:
            holidays = nseholidayspxy.get_nse_fo_holidays(date(2026, 10, 12))

        self.assertEqual(holidays, frozenset({date(2026, 10, 20)}))
        fetch.assert_called_once_with()

    def test_fails_explicitly_when_fetch_fails_without_cached_calendar(self):
        with patch.object(
            nseholidayspxy, "_fetch_holidays", side_effect=OSError("offline")
        ):
            with self.assertRaisesRegex(RuntimeError, "no cached calendar"):
                nseholidayspxy.get_nse_fo_holidays(date(2026, 10, 12))

    def test_parses_nse_fo_dates(self):
        payload = json.dumps(
            {
                "FO": [
                    {"tradingDate": "20-Oct-2026"},
                    {"tradingDate": "10-Nov-2026"},
                ]
            }
        )
        self.assertEqual(
            nseholidayspxy._parse_holidays(payload),
            frozenset({date(2026, 10, 20), date(2026, 11, 10)}),
        )


if __name__ == "__main__":
    unittest.main()
