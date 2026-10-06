# exeotmpxy.py
import sys
from pathlib import Path

SYS_DIR = Path(__file__).resolve().parents[1]
if str(SYS_DIR) not in sys.path:
    sys.path.insert(0, str(SYS_DIR))

from syscnfgpxy import (
    EXEOTMPXY_DEFAULT_DISTANCE,
)

def get_dynamic_otm_distance():
    """Return the configured OTM distance."""
    return EXEOTMPXY_DEFAULT_DISTANCE
