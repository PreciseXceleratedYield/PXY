import sys
import unittest
from pathlib import Path

SYS_DIR = Path(__file__).resolve().parents[1]
if str(SYS_DIR) not in sys.path:
    sys.path.insert(0, str(SYS_DIR))
EXE_DIR = SYS_DIR / "exe"
if str(EXE_DIR) not in sys.path:
    sys.path.insert(0, str(EXE_DIR))

from exetgtpxy import target_price


class TargetPriceTests(unittest.TestCase):
    def test_aligned_targets_use_one_atr_percent_for_each_option_side(self):
        cases = (
            ({"symbol": "NIFTY26OCT25000CE", "exit": "BULL"}, 105.0),
            ({"symbol": "NIFTY26OCT25000PE", "exit": "BEAR"}, 105.0),
        )
        for market, expected in cases:
            with self.subTest(symbol=market["symbol"]):
                row = {
                    **market,
                    "pxy_entry": 100.0,
                    "atr": 5.0,
                }
                self.assertEqual(target_price(row), expected)

    def test_unaligned_targets_keep_configured_percentage(self):
        row = {
            "symbol": "NIFTY26OCT25000CE",
            "exit": "SIDE",
            "pxy_entry": 100.0,
            "atr": 5.0,
        }
        self.assertEqual(target_price(row), 101.4)

    def test_target_pct_is_clamped_between_floor_and_atr(self):
        row = {
            "symbol": "NIFTY26OCT25000CE",
            "exit": "BULL",
            "pxy_entry": 100.0,
            "atr": 3.0,
        }
        self.assertEqual(target_price(row), 103.0)

        row["atr"] = 0.5
        self.assertEqual(target_price(row), 101.4)

    def test_heavier_side_uses_floor_while_lighter_side_preserves_reserve(self):
        heavier_ce = {
            "symbol": "NIFTY26OCT25000CE",
            "exit": "BULL",
            "pxy_entry": 100.0,
            "atr": 5.0,
        }
        lighter_pe = {
            "symbol": "NIFTY26OCT25000PE",
            "exit": "BEAR",
            "pxy_entry": 100.0,
            "atr": 5.0,
        }

        self.assertEqual(target_price(heavier_ce, ce_investment=200.0, pe_investment=100.0), 101.4)
        self.assertEqual(target_price(lighter_pe, ce_investment=100.0, pe_investment=200.0), 101.4)


if __name__ == "__main__":
    unittest.main()
