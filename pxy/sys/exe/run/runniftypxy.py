# run/runsymbpxy.py
from datetime import datetime, date, timedelta

# ---------------- CONFIG ----------------
STRIKE_STEP = 50 
HOLIDAYS = [
    "26-Jan-2026", "06-Mar-2026", "20-Mar-2026", "31-Mar-2026",
    "03-Apr-2026", "14-Apr-2026", "01-May-2026", "15-Aug-2026",
    "02-Oct-2026", "21-Oct-2026", "06-Nov-2026", "24-Nov-2026", "25-Dec-2026"
]
HOLIDAYS = [datetime.strptime(h, "%d-%b-%Y").date() for h in HOLIDAYS]

# ---------------- HELPERS ----------------

def get_target_tuesday():
    """Calculates the Tuesday of the FOLLOWING week."""
    today = date.today()
    days_until_tue = (1 - today.weekday() + 7) % 7
    
    # Always target NEXT week's Tuesday
    if today.weekday() <= 1:
        days_until_tue += 7
        
    target_tue = today + timedelta(days=days_until_tue)
    
    # Holiday Adjustment: Move to previous trading day
    while target_tue in HOLIDAYS:
        target_tue -= timedelta(days=1)
    return target_tue

def is_monthly_expiry(expiry_date):
    """Checks if the date is the last Tuesday of its month."""
    return (expiry_date + timedelta(days=7)).month != expiry_date.month

# ---------------- MAIN SYMBOL BUILDER ----------------

def get_symbol(price, side):
    """
    Main entry point for Kotak Neo Symbol Generation.
    Takes (price, side) -> Returns Nifty Symbol String
    """
    try:
        if not price or price == 0: return "NA"
        
        side = str(side).upper()
        opt_type = "CE" if side in ["BUY", "CE"] else "PE" if side in ["SELL", "PE"] else None
        if not opt_type: return "NA"

        # 1. Strike Rounding
        atm_strike = int(round(float(price) / STRIKE_STEP) * STRIKE_STEP)
        
        # 2. Expiry Calculation
        expiry = get_target_tuesday()
        yy = str(expiry.year)[-2:]

        # 3. Format Selection (Monthly vs Weekly)
        if is_monthly_expiry(expiry):
            mm_str = expiry.strftime('%b').upper() 
            return f"NIFTY{yy}{mm_str}{atm_strike}{opt_type}"
        else:
            month_map = {10: "O", 11: "N", 12: "D"}
            mm_char = month_map.get(expiry.month, str(expiry.month))
            dd_str = f"{expiry.day:02d}"
            return f"NIFTY{yy}{mm_char}{dd_str}{atm_strike}{opt_type}"

    except Exception as e:
        print(f"❌ Symbol Generation Error: {e}")
        return "NA"
