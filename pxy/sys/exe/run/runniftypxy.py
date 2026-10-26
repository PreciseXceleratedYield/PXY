
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
    # Preserve the existing nearest-strike rounding.
    return int(round(float(price) / STRIKE_STEP) * STRIKE_STEP)


# ---------------- MAIN ----------------

def get_symbol(price, side, otm_distance=None):
    """
    Build an option symbol using the configured strike policy by default.

    When otm_distance is explicitly supplied, use it as the strike offset
    for this call. Preserve the existing expiry and symbol construction.
    """
    try:
        if not price or price == 0:
            return "NA"

        side = str(side).upper().strip()

        # ---------------- SIGNAL MAP ----------------
        if side in ["ATMBUY", "OTMBUY"]:
            opt_type = "CE"
        elif side in ["ATMSELL", "OTMSELL"]:
            opt_type = "PE"
        else:
            return "NA"

        # ---------------- STRIKE RESOLUTION ----------------
        strike_mode = get_strike_mode()

        if otm_distance is None:
            # No explicit offset: preserve the configured strike policy.
            distance = get_dynamic_otm_distance()
            use_offset = strike_mode != "ATM"
        else:
            # Explicit offset: override the configured strike distance.
            if isinstance(otm_distance, bool):
                raise ValueError("Strike offset must be a non-negative number.")

            distance = float(otm_distance)

            if distance < 0 or not distance.is_integer():
                raise ValueError("Strike offset must be a non-negative whole number.")

            use_offset = True

        # Establish the existing raw baseline price plus daily buffer.
        raw_base = float(price) + float(ATM_BUFFER)

        # Apply the selected offset only to the numeric strike.
        if use_offset:
            if opt_type == "CE":
                raw_strike = raw_base + distance
            else:
                raw_strike = raw_base - distance
        else:
            raw_strike = raw_base

        # Preserve existing strike rounding.
        strike = round_to_strike(raw_strike)

        # ---------------- EXPIRY ----------------
        expiry = get_target_tuesday()
        yy = str(expiry.year)[-2:]

        # ---------------- FORMAT ----------------
        if is_monthly_expiry(expiry):
            mm_str = expiry.strftime('%b').upper()
            return f"NIFTY{yy}{mm_str}{strike}{opt_type}"
        else:
            month_map = {10: "O", 11: "N", 12: "D"}
            mm_char = month_map.get(expiry.month, str(expiry.month))
            dd_str = f"{expiry.day:02d}"
            return f"NIFTY{yy}{mm_char}{dd_str}{strike}{opt_type}"

    except Exception as e:
        print(f"❌ Symbol Generation Error: {e}")
        return "NA"
