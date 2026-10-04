#!/usr/bin/env python3
"""Direct backtest runner - sets SIM mode and runs replay without engine dispatch."""
import os
import sys
from pathlib import Path

# Force SIM mode immediately
os.environ["RUNMODE"] = "SIM"

SYS_DIR = Path(__file__).resolve().parent / "pxy" / "sys"
if str(SYS_DIR) not in sys.path:
    sys.path.insert(0, str(SYS_DIR))

from tstmodepxy.backtest import main

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
