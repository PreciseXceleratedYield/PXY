from datetime import datetime, date, timedelta

# ---------------- CONFIG ----------------
STRIKE_STEP = 100
ATM_BUFFER = 0

HOLIDAYS = [
    "26-Jan-2026", "06-Mar-2026", "20-Mar-2026", "31-Mar-2026",
    "03-Apr-2026", "14-Apr-2026", "01-May-2026", "15-Aug-2026",
    "02-Oct-2026", "21-Oct-2026", "06-Nov-2026", "24-Nov-2026", "25-Dec-2026"
]

HOLIDAYS = [datetime.strptime(h, "%d-%b-%Y").date() for h in HOLIDAYS]


# ---------------- EXPIRY ----------------
def get_monthly_expiry():
    today = date.today()

    if today.day <= 24:
        target_month = today.month
        target_year = today.year
    else:
        if today.month == 12:
            target_month = 1
            target_year = today.year + 1
        else:
            target_month = today.month + 1
            target_year = today.year

    if target_month == 12:
        next_month = date(target_year + 1, 1, 1)
    else:
        next_month = date(target_year, target_month + 1, 1)

    last_day = next_month - timedelta(days=1)

    offset = (last_day.weekday() - 3) % 7
    expiry = last_day - timedelta(days=offset)

    while expiry in HOLIDAYS:
        expiry -= timedelta(days=1)

    return expiry


def is_monthly_expiry(expiry_date):
    return True


def round_to_strike(price):
    return int(round(float(price) / STRIKE_STEP) * STRIKE_STEP)


# ---------------- MAIN SYMBOL BUILDER ----------------
def get_symbol(price, side, otm_distance):
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

        # ---------------- ATM ----------------
        atm = round_to_strike(price)
        atm = atm + ATM_BUFFER

        # ---------------- OTM SHIFT ----------------
        if "OTM" in side:
            if opt_type == "CE":
                strike = atm + otm_distance
            else:
                strike = atm - otm_distance
        else:
            strike = atm

        # ---------------- EXPIRY ----------------
        expiry = get_monthly_expiry()
        yy = str(expiry.year)[-2:]
        mm_str = expiry.strftime('%b').upper()

        return f"BANKNIFTY{yy}{mm_str}{strike}{opt_type}"

    except Exception as e:
        print(f"❌ BANK Symbol Error: {e}")
        return "NA"
