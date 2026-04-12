# run/runsymbpxy.py
from datetime import datetime, date, timedelta

# ---------------- CONFIG ----------------
STRIKE_STEP = 50

# FIXED OTM DISTANCE (your requirement)
OTM_DISTANCE = 200  

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
    return int(round(float(price) / STRIKE_STEP) * STRIKE_STEP)


# ---------------- MAIN ----------------

def get_symbol(price, side):
    """
    Signal-driven symbol builder:
    - ATM = base strike + buffer
    - OTM = ATM ± fixed 200 points
    """

    try:
        if not price or price == 0:
            return "NA"

        side = str(side).upper().strip()

        # ---------------- SIGNAL MAP ----------------
        if side in ["ATMBUY", "OTMBUY"]:
            opt_type = "CE"
            mode = "ATM"

        elif side in ["ATMSELL", "OTMSELL"]:
            opt_type = "PE"
            mode = "ATM"

        else:
            return "NA"

        # ---------------- ATM BASE ----------------
        atm = round_to_strike(price)

        # apply daily buffer
        atm_adjusted = atm + ATM_BUFFER

        # ---------------- OTM SHIFT ----------------
        if "OTM" in side:
            if opt_type == "CE":
                strike = atm_adjusted + OTM_DISTANCE
            else:
                strike = atm_adjusted - OTM_DISTANCE
        else:
            strike = atm_adjusted

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
