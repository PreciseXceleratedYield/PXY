# run/runbankpxy.py

from datetime import datetime, date, timedelta

# ---------------- CONFIG ----------------
STRIKE_STEP = 100 

HOLIDAYS = [
    "26-Jan-2026", "03-Mar-2026", "26-Mar-2026", "31-Mar-2026",
    "03-Apr-2026", "14-Apr-2026", "01-May-2026", "28-May-2026",
    "26-Jun-2026", "14-Sep-2026", "02-Oct-2026", "20-Oct-2026", 
    "10-Nov-2026", "24-Nov-2026", "25-Dec-2026"
]
HOLIDAYS = [datetime.strptime(h, "%d-%b-%Y").date() for h in HOLIDAYS]

# ---------------- HELPERS ----------------

def get_last_tuesday(year, month):
    if month == 12:
        last_day = date(year, 12, 31)
    else:
        last_day = date(year, month + 1, 1) - timedelta(days=1)
    
    offset = (last_day.weekday() - 1) % 7
    last_tue = last_day - timedelta(days=offset)
    
    while last_tue in HOLIDAYS or last_tue.weekday() >= 5:
        last_tue -= timedelta(days=1)
    return last_tue

# ---------------- MAIN ----------------

def get_symbol(price, side):
    try:
        if not price or price == 0:
            return "NA"
        
        side = str(side).upper()
        opt_type = "CE" if side in ["BUY", "CE", "CALL"] else \
                   "PE" if side in ["SELL", "PE", "PUT"] else None
        
        if not opt_type:
            return "NA"

        atm_strike = int(round(float(price) / STRIKE_STEP) * STRIKE_STEP)
        
        today = date.today()
        expiry = get_last_tuesday(today.year, today.month)
        
        if today > expiry:
            next_month = today.month + 1 if today.month < 12 else 1
            next_year = today.year if today.month < 12 else today.year + 1
            expiry = get_last_tuesday(next_year, next_month)

        yy = str(expiry.year)[-2:]
        mm_str = expiry.strftime('%b').upper()
        
        return f"BANKNIFTY{yy}{mm_str}{atm_strike}{opt_type}"

    except Exception as e:
        print(f"❌ BANK Symbol Error: {e}")
        return "NA"
