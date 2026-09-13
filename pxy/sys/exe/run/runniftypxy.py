import sys
from pathlib import Path
from datetime import datetime, date, timedelta

# ---------------- CONFIG ----------------
# Adjusted to 50 to allow valid Nifty 50-point step intervals while locking the last digit to 0
STRIKE_STEP = 50

# DAILY ATM BUFFER (you can change daily without touching logic)
ATM_BUFFER = 0  

# HOLIDAYS
HOLIDAYS = [
    "26-Jan-2026", "06-Mar-2026", "20-Mar-2026", "31-Mar-2026",
    "03-Apr-2026", "14-Apr-2026", "01-May-2026", "15-Aug-2026",
    "02-Oct-2026", "21-Oct-2026", "06-Nov-2026", "24-Nov-2026", "25-Dec-2026"
]
HOLIDAYS = [datetime.strptime(h, "%d-%b-%Y").date() for h in HOLIDAYS]

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

def get_symbol(price, side, otm_distance):
    """
    Signal-driven symbol builder:
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

        # ---------------- STRIKE RESOLUTION ----------------
        # 1. Establish the raw baseline price plus your daily buffer
        raw_base = float(price) + float(ATM_BUFFER)

        # 2. Add or subtract the weekday distance offset first in pure float arithmetic
        if "OTM" in side:
            if opt_type == "CE":
                raw_strike = raw_base + float(otm_distance)
            else:
                raw_strike = raw_base - float(otm_distance)
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
