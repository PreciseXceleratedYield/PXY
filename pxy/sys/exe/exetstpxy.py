#!/usr/bin/env python3
"""Standalone offline runner for the ten TST pipe scenarios."""

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SYS_DIR = HERE.parent
for path in (HERE, SYS_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from syscnfgpxy import RUNNIFTYPXY_HOLIDAYS
from tstmodepxy.pipescenarios import run_tst_entrypoint


def main():
    result = run_tst_entrypoint(RUNNIFTYPXY_HOLIDAYS)
    if result is None:
        return 2
    return 0 if result else 1


if __name__ == "__main__":
    raise SystemExit(main())
