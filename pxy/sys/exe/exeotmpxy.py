# exeotmpxy.py
import sys
from datetime import date, datetime
from pathlib import Path

SYS_DIR = Path(__file__).resolve().parents[1]
if str(SYS_DIR) not in sys.path:
    sys.path.insert(0, str(SYS_DIR))

import syscnfgpxy


def get_strike_mode():
    """Return the validated strike-selection mode used by all option buys."""
    mode = str(getattr(syscnfgpxy, "EXEOTMPXY_STRIKE_MODE", "ATM")).strip().upper()
    if mode not in {"ATM", "OTMFIX", "OTMDYN"}:
        raise ValueError(f"Unsupported option strike mode: {mode}")
    return mode


def get_dynamic_otm_distance(trade_date=None):
    """Return the mode's offset in NIFTY points; dynamic offsets use Mon-Fri order."""
    mode = get_strike_mode()
    if mode == "ATM":
        return 0
    if mode == "OTMFIX":
        distance = getattr(
            syscnfgpxy,
            "EXEOTMPXY_FIXED_DISTANCE",
            getattr(syscnfgpxy, "EXEOTMPXY_DEFAULT_DISTANCE", 100),
        )
    else:
        if trade_date is None:
            timezone = getattr(syscnfgpxy, "SYSCNFGPXY_TIMEZONE")
            trade_date = datetime.now(timezone).date()
        if not isinstance(trade_date, date):
            raise TypeError("trade_date must be a datetime.date")
        weekday = trade_date.weekday()
        distances = getattr(
            syscnfgpxy,
            "EXEOTMPXY_DYNAMIC_WEEKDAY_DISTANCES",
            (200, 150, 100, 50, 0),
        )
        if weekday >= len(distances):
            raise ValueError("Dynamic OTM distance is only defined Monday through Friday.")
        distance = distances[weekday]

    if isinstance(distance, bool) or not isinstance(distance, (int, float)) or distance < 0:
        raise ValueError("OTM distance must be a non-negative number.")
    return distance
