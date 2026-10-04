# exeotmpxy.py
from datetime import datetime
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
