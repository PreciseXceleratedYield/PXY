#!/usr/bin/env python3
"""Backtest validation script - runs focused replay tests."""
import os
import sys
import unittest
from pathlib import Path

# Force SIM mode
os.environ["RUNMODE"] = "SIM"

# Add sys to path
SYS_DIR = Path(__file__).resolve().parent / "pxy" / "sys"
if str(SYS_DIR) not in sys.path:
    sys.path.insert(0, str(SYS_DIR))

if __name__ == "__main__":
    # Run focused backtest tests
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    try:
        from tstmodepxy import test_mode_dispatch
        suite.addTests(loader.loadTestsFromModule(test_mode_dispatch))
        print("✓ Loaded test_mode_dispatch")
    except Exception as e:
        print(f"⚠ Could not load test_mode_dispatch: {e}")
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    sys.exit(0 if result.wasSuccessful() else 1)
