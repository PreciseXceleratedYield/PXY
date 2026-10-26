
import sys
from pathlib import Path
from datetime import date, timedelta

SYS_DIR = Path(__file__).resolve().parents[2]
EXE_DIR = SYS_DIR / "exe"
if str(SYS_DIR) not in sys.path:
    sys.path.insert(0, str(SYS_DIR))
if str(EXE_DIR) not in sys.path:
    sys.path.insert(0, str(EXE_DIR))

from exeotmpxy import get_dynamic_otm_distance, get_strike_mode
from nseholidayspxy import get_nse_fo_holidays
from syscnfgpxy import (
    RUNNIFTYPXY_ATM_BUFFER,
    RUNNIFTYPXY_STRIKE_STEP,
)

STRIKE_STEP = RUNNIFTYPXY_STRIKE_STEP
ATM_BUFFER = RUNNIFTYPXY_ATM_BUFFER


# ---------------- HELPERS ----------------

def get_target_tuesday():
    today = date.today()
    days_until_tue = (1 - today.weekday() + 7) % 7

    if today.weekday() <= 1:
        days_until_tue += 7

    target_tue = today + timedelta(days=days_until_tue)

    while target_tue in get_nse_fo_holidays():
        target_tue -= timedelta(days=1)

    return target_tue


def is_monthly_expiry(expiry_date):
    return (expiry_date + timedelta(days=7)).month != expiry_date.month


def round_to_strike(price):
    # Snap to the nearest configured strike interval.
    return int(round(float(price) / STRIKE_STEP) * STRIKE_STEP)


# ---------------- MAIN ----------------

def get_symbol(price, side, otm_distance=None):
    """
    Build an option symbol using the configured strike policy by default.

    If otm_distance is supplied, use that explicit non-negative whole-number
    offset instead of the configured strike distance or ATM mode.

    CE: baseline price + offset
    PE: baseline price - offset

    The final strike is rounded to the configured strike interval.
    """
    try:
        if price is None or price == 0:
            return "NA"

        side = str(side).upper().strip()

        # ---------------- SIGNAL MAP ----------------
        if side in ["ATMBUY", "OTMBUY"]:
            opt_type = "CE"
        elif side in ["ATMSELL", "OTMSELL"]:
            opt_type = "PE"
        else:
            return "NA"

        # ---------------- STRIKE MODE / DISTANCE ----------------
        strike_mode = get_strike_mode()

        if otm_distance is None:
            distance = get_dynamic_otm_distance()
            use_offset = strike_mode != "ATM"
        else:
            if (
                isinstance(otm_distance, bool)
                or not isinstance(otm_distance, int)
                or otm_distance < 0
            ):
                raise ValueError(
                    "OTM distance must be a non-negative whole number."
                )

            distance = otm_distance
            use_offset = True

        # ---------------- STRIKE RESOLUTION ----------------
        # Establish the raw baseline price plus the configured buffer.
        raw_base = float(price) + float(ATM_BUFFER)

        # An explicit offset takes precedence over the configured strike mode.
        # Without an explicit offset, preserve the configured ATM/OTM behavior.
        if use_offset:
            if opt_type == "CE":
                raw_strike = raw_base + float(distance)
            else:
                raw_strike = raw_base - float(distance)
        else:
            raw_strike = raw_base

        # Round to the configured strike interval.
        strike = round_to_strike(raw_strike)

        # ---------------- EXPIRY ----------------
        expiry = get_target_tuesday()
        yy = str(expiry.year)[-2:]

        # ---------------- FORMAT ----------------
        if is_monthly_expiry(expiry):
            mm_str = expiry.strftime("%b").upper()
            return f"NIFTY{yy}{mm_str}{strike}{opt_type}"
        else:
            month_map = {10: "O", 11: "N", 12: "D"}
            mm_char = month_map.get(expiry.month, str(expiry.month))
            dd_str = f"{expiry.day:02d}"
            return f"NIFTY{yy}{mm_char}{dd_str}{opt_type}"

    except Exception as e:
        print(f"❌ Symbol Generation Error: {e}")
        return "NA"
