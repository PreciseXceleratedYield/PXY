# exeotmpxy.py
import sys
from datetime import datetime
from pathlib import Path

SYS_DIR = Path(__file__).resolve().parents[1]
if str(SYS_DIR) not in sys.path:
    sys.path.insert(0, str(SYS_DIR))

from syscnfgpxy import (
    EXEOTMPXY_DEFAULT_DISTANCE,
    EXEOTMPXY_DISTANCE_BY_WEEKDAY,
    SYSCNFGPXY_TIMEZONE,
)

def get_dynamic_otm_distance():
    """Return the configured fixed 100-point OTM distance for every weekday."""
    # Force timezone validation to prevent errors on overseas servers (e.g., VPS)
    ist = SYSCNFGPXY_TIMEZONE
    current_day = datetime.now(ist).weekday()
    return EXEOTMPXY_DISTANCE_BY_WEEKDAY.get(
        current_day, EXEOTMPXY_DEFAULT_DISTANCE
    )
