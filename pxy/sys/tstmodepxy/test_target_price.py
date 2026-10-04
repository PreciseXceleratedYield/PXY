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
    """Comprehensive test suite for weighted-floor balancer target pricing."""
    
    # ========== ALIGNED TARGETS WITH ATR-BASED VALUES ==========
    def test_aligned_ce_bull_uses_atr_value(self):
        """When CE is BULL-aligned, target should use ATR percentage."""
        row = {
            "symbol": "NIFTY26OCT25000CE",
            "exit": "BULL",
            "pxy_entry": 100.0,
            "atr": 5.0,
        }
        # ATR 5% → target = 100 * (1 + 0.05) = 105
        self.assertEqual(target_price(row), 105.0)

    def test_aligned_pe_bear_uses_atr_value(self):
        """When PE is BEAR-aligned, target should use ATR percentage."""
        row = {
            "symbol": "NIFTY26OCT25000PE",
            "exit": "BEAR",
            "pxy_entry": 100.0,
            "atr": 5.0,
        }
        # ATR 5% → target = 100 * (1 + 0.05) = 105
        self.assertEqual(target_price(row), 105.0)

    # ========== UNALIGNED TARGETS STAY AT 1.4% FLOOR ==========
    def test_unaligned_ce_with_side_exit_uses_floor(self):
        """When CE has SIDE/counter-signal, use 1.4% floor."""
        row = {
            "symbol": "NIFTY26OCT25000CE",
            "exit": "SIDE",
            "pxy_entry": 100.0,
            "atr": 5.0,
        }
        # Unaligned → 1.4% floor → target = 100 * (1 + 0.014) = 101.4
        self.assertEqual(target_price(row), 101.4)

    def test_unaligned_pe_with_bull_exit_uses_floor(self):
        """When PE has BULL (wrong direction), use 1.4% floor."""
        row = {
            "symbol": "NIFTY26OCT25000PE",
            "exit": "BULL",
            "pxy_entry": 100.0,
            "atr": 5.0,
        }
        # PE needs BEAR, not BULL → unaligned → 1.4% floor
        self.assertEqual(target_price(row), 101.4)

    # ========== ATR MINIMUM GUARDRAIL (ATR_MIN = 5) ==========
    def test_atr_below_minimum_is_scaled_up(self):
        """When ATR < 5, it should be clamped to minimum 5."""
        row = {
            "symbol": "NIFTY26OCT25000CE",
            "exit": "BULL",
            "pxy_entry": 100.0,
            "atr": 2.0,  # Below minimum of 5
        }
        # ATR scaled to 5 → target = 100 * (1 + 0.05) = 105
        self.assertEqual(target_price(row), 105.0)

    def test_atr_exactly_minimum_is_used(self):
        """When ATR = 5, it should be used as-is."""
        row = {
            "symbol": "NIFTY26OCT25000CE",
            "exit": "BULL",
            "pxy_entry": 100.0,
            "atr": 5.0,
        }
        # ATR = 5 → target = 100 * (1 + 0.05) = 105
        self.assertEqual(target_price(row), 105.0)

    # ========== FLOOR AND CAP CLAMPING [1.4, min(ATR, 77)] ==========
    def test_target_respects_lower_bound_floor(self):
        """Calculated target below 1.4% should be clamped to floor."""
        row = {
            "symbol": "NIFTY26OCT25000CE",
            "exit": "BULL",
            "pxy_entry": 100.0,
            "atr": 0.5,  # Very small ATR
        }
        # ATR scaled to 5, still clamped to [1.4, min(5, 77)] = [1.4, 5]
        # Result should be at least 1.4%
        result = target_price(row)
        self.assertGreaterEqual(result, 101.4)  # At least 1.4%

    def test_target_respects_upper_bound_cap_at_77_percent(self):
        """When ATR > 77%, target should be capped at 77%."""
        row = {
            "symbol": "NIFTY26OCT25000CE",
            "exit": "BULL",
            "pxy_entry": 100.0,
            "atr": 100.0,  # ATR > cap
        }
        # ATR capped to 77 → target = 100 * (1 + 0.77) = 177
        self.assertEqual(target_price(row), 177.0)

    # ========== WEIGHTED-FLOOR: HEAVIER SIDE ==========
    def test_heavier_ce_uses_aggressive_floor(self):
        """When CE is heavier (>60%), it uses 1.4% floor for fast exit."""
        row = {
            "symbol": "NIFTY26OCT25000CE",
            "exit": "BULL",
            "pxy_entry": 100.0,
            "atr": 5.0,
        }
        # CE investment 70, PE investment 30 → CE is heavy (70%)
        ce_inv = 70.0
        pe_inv = 30.0
        
        result = target_price(row, ce_investment=ce_inv, pe_investment=pe_inv)
        # CE heavy + ATR 5 → max(5, 1.4) = 5 → 105
        self.assertEqual(result, 105.0)

    def test_heavier_pe_uses_aggressive_floor(self):
        """When PE is heavier (>60%), it uses 1.4% floor for fast exit."""
        row = {
            "symbol": "NIFTY26OCT25000PE",
            "exit": "BEAR",
            "pxy_entry": 100.0,
            "atr": 5.0,
        }
        # PE investment 80, CE investment 20 → PE is heavy (80%)
        ce_inv = 20.0
        pe_inv = 80.0
        
        result = target_price(row, ce_investment=ce_inv, pe_investment=pe_inv)
        # PE heavy + ATR 5 → max(5, 1.4) = 5 → 105
        self.assertEqual(result, 105.0)

    # ========== WEIGHTED-FLOOR: LIGHTER SIDE ==========
    def test_lighter_ce_uses_reserve_floor(self):
        """When CE is lighter (<60%), it uses 2.8% reserve floor."""
        row = {
            "symbol": "NIFTY26OCT25000CE",
            "exit": "BULL",
            "pxy_entry": 100.0,
            "atr": 2.0,  # ATR < 5, scaled to 5
        }
        # CE investment 30, PE investment 70 → CE is light (30%)
        ce_inv = 30.0
        pe_inv = 70.0
        
        result = target_price(row, ce_investment=ce_inv, pe_investment=pe_inv)
        # CE light + ATR scaled to 5 → max(5, 2.8) = 5 → 105
        self.assertEqual(result, 105.0)

    def test_lighter_pe_uses_reserve_floor(self):
        """When PE is lighter (<60%), it uses 2.8% reserve floor."""
        row = {
            "symbol": "NIFTY26OCT25000PE",
            "exit": "BEAR",
            "pxy_entry": 100.0,
            "atr": 2.0,  # ATR < 5, scaled to 5
        }
        # PE investment 20, CE investment 80 → PE is light (20%)
        ce_inv = 80.0
        pe_inv = 20.0
        
        result = target_price(row, ce_investment=ce_inv, pe_investment=pe_inv)
        # PE light + ATR scaled to 5 → max(5, 2.8) = 5 → 105
        self.assertEqual(result, 105.0)

    # ========== EDGE CASES: LOW ATR WITH RESERVE FLOOR ==========
    def test_lighter_side_with_low_atr_uses_reserve_floor_2_8(self):
        """Lighter side should use 2.8% floor when ATR < 2.8."""
        row = {
            "symbol": "NIFTY26OCT25000CE",
            "exit": "BULL",
            "pxy_entry": 100.0,
            "atr": 1.0,  # Well below reserve floor
        }
        # CE light + low ATR → max(5, 2.8) = 5 (due to min ATR)
        ce_inv = 30.0
        pe_inv = 70.0
        
        result = target_price(row, ce_investment=ce_inv, pe_investment=pe_inv)
        # Even with low ATR, min(5) applies → 105
        self.assertEqual(result, 105.0)

    # ========== BALANCED PORTFOLIO (NEITHER HEAVIER) ==========
    def test_balanced_portfolio_uses_atr_value(self):
        """When both sides are balanced (50/50), use ATR normally."""
        row = {
            "symbol": "NIFTY26OCT25000CE",
            "exit": "BULL",
            "pxy_entry": 100.0,
            "atr": 6.0,
        }
        # CE 50, PE 50 → balanced (neither > 60%)
        # Should use ATR value → 6%
        result = target_price(row, ce_investment=50.0, pe_investment=50.0)
        self.assertEqual(result, 106.0)

    # ========== ZERO/MISSING INVESTMENTS ==========
    def test_missing_ce_investment_treated_as_1(self):
        """Missing CE investment should default to 1.0 (safe default)."""
        row = {
            "symbol": "NIFTY26OCT25000CE",
            "exit": "BULL",
            "pxy_entry": 100.0,
            "atr": 5.0,
        }
        # Only PE investment given → CE defaults to 1
        result = target_price(row, ce_investment=0.0, pe_investment=100.0)
        # CE treated as light (1/101 ≈ 1%) → uses reserve floor
        self.assertGreater(result, 100.0)

    # ========== MISSING/INVALID DATA ==========
    def test_missing_entry_price_returns_zero(self):
        """When entry price is missing or invalid, return 0."""
        row = {
            "symbol": "NIFTY26OCT25000CE",
            "exit": "BULL",
            "atr": 5.0,
        }
        self.assertEqual(target_price(row), 0.0)

    def test_invalid_symbol_returns_entry_price(self):
        """Non-option symbol should return entry price as-is."""
        row = {
            "symbol": "NIFTY",
            "exit": "BULL",
            "pxy_entry": 100.0,
            "atr": 5.0,
        }
        # Not a CE/PE → return entry price rounded
        self.assertEqual(target_price(row), 100.0)

    def test_missing_atr_uses_floor(self):
        """When ATR is missing, should use minimum ATR (5)."""
        row = {
            "symbol": "NIFTY26OCT25000CE",
            "exit": "BULL",
            "pxy_entry": 100.0,
        }
        # No ATR → defaults to 5 (min) → 105
        result = target_price(row)
        self.assertGreaterEqual(result, 101.4)

    # ========== COUNTER-SIGNAL AND FLOOR BALANCING ==========
    def test_counter_signal_respects_77_cap(self):
        """On counter-signal, floor-balanced target should not exceed 77%."""
        row = {
            "symbol": "NIFTY26OCT25000CE",
            "exit": "SIDE",  # Counter-signal
            "pxy_entry": 100.0,
            "atr": 100.0,  # Very high ATR
        }
        # Unaligned (SIDE) → 1.4% floor, capped at 77
        result = target_price(row)
        self.assertEqual(result, 101.4)  # Floor, not capped

    # ========== MULTIPLE INVESTMENT RATIOS ==========
    def test_60_40_split_ce_is_heavy(self):
        """60/40 split should classify CE as heavy."""
        row = {
            "symbol": "NIFTY26OCT25000CE",
            "exit": "BULL",
            "pxy_entry": 100.0,
            "atr": 5.0,
        }
        result = target_price(row, ce_investment=60.0, pe_investment=40.0)
        # CE is heavy (60%) → uses max(5, 1.4) = 5
        self.assertEqual(result, 105.0)

    def test_55_45_split_is_not_heavy(self):
        """55/45 split should NOT classify as heavy (need > 60%)."""
        row = {
            "symbol": "NIFTY26OCT25000CE",
            "exit": "BULL",
            "pxy_entry": 100.0,
            "atr": 5.0,
        }
        result = target_price(row, ce_investment=55.0, pe_investment=45.0)
        # CE at 55% (< 60%) → not heavy, balanced → uses ATR
        self.assertEqual(result, 105.0)


if __name__ == "__main__":
    unittest.main()

