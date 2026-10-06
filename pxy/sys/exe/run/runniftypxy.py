import sys
from pathlib import Path
from datetime import datetime, date, timedelta

SYS_DIR = Path(__file__).resolve().parents[2]
EXE_DIR = SYS_DIR / "exe"
if str(SYS_DIR) not in sys.path:
    sys.path.insert(0, str(SYS_DIR))
if str(EXE_DIR) not in sys.path:
    sys.path.insert(0, str(EXE_DIR))

from exeotmpxy import get_dynamic_otm_distance, get_strike_mode
from syscnfgpxy import (
    RUNNIFTYPXY_ATM_BUFFER,
    RUNNIFTYPXY_HOLIDAYS,
    RUNNIFTYPXY_STRIKE_STEP,
)

STRIKE_STEP = RUNNIFTYPXY_STRIKE_STEP
ATM_BUFFER = RUNNIFTYPXY_ATM_BUFFER
HOLIDAYS = [
    datetime.strptime(h, "%d-%b-%Y").date() for h in RUNNIFTYPXY_HOLIDAYS
]

# ---------------- HELPERS ----------------

def get_target_tuesday():
    today = date.today()
    days_until_tue = (1 - today.weekday() + 7) % 7

    if today.weekday() <= 1:
        days_until_tue += 7

    target_tue = today + timedelta(days=days_until_tue)

    while target_tue in HOLIDAYS:
        target_tue -= timedelta(days=1)

    return target_tue


def is_monthly_expiry(expiry_date):
    return (expiry_date + timedelta(days=7)).month != expiry_date.month


def round_to_strike(price):
    # Snaps directly to the nearest 50 interval (Ensures the last digit is always 0)
    return int(round(float(price) / STRIKE_STEP) * STRIKE_STEP)


# ---------------- MAIN ----------------

def get_symbol(price, side, otm_distance=None):
    """
    Build an option symbol using the centrally configured strike mode.
    `otm_distance` remains accepted for compatibility but cannot override config.

    - Math is accumulated directly first (Price + Buffer ± Weekday Distance)
    - Enforces valid exchange tracking by rounding to the nearest 50 step at the end.
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

        # The central mode overrides caller-supplied OTM flags/distances so no
        # buying script can bypass the configured strike policy.
        strike_mode = get_strike_mode()
        distance = get_dynamic_otm_distance()

        # ---------------- STRIKE RESOLUTION ----------------
        # 1. Establish the raw baseline price plus your daily buffer
        raw_base = float(price) + float(ATM_BUFFER)

        # 2. Apply the centrally configured fixed/dynamic offset.
        if strike_mode != "ATM":
            if opt_type == "CE":
                raw_strike = raw_base + float(distance)
            else:
                raw_strike = raw_base - float(distance)
        else:
            raw_strike = raw_base

        # 3. Round to nearest 50 later (Guarantees last digit is 0, allowing both xx00 and xx50)
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
