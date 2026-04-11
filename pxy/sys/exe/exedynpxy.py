from datetime import datetime
import pytz
import math

IST = pytz.timezone("Asia/Kolkata")

# ---------------- CONFIG ----------------
MAX_SECONDS = 4 * 60 * 60   # 4 hours window
MIN_INC = 0.0001
MAX_INC = 0.01
K = 5  # exponential curvature (higher = sharper late decay)
# ----------------------------------------


def get_dynamic_increment(elapsed_secs):
    """
    Exponential acceleration from MIN_INC → MAX_INC over 4 hours.
    """
    t = min(elapsed_secs / MAX_SECONDS, 1.0)

    # exponential easing
    exp_val = math.exp(K * t) - 1
    exp_max = math.exp(K) - 1

    factor = exp_val / exp_max  # normalize 0 → 1

    return MIN_INC + (MAX_INC - MIN_INC) * factor


def dynamic_entry(row):
    try:
        original_price = float(row.get("buy_prc", 0))
        entry_time_val = row.get("buy_time")
        symbol = str(row.get("symbol", "")).upper()

        if not entry_time_val or original_price == 0:
            return original_price

        now = datetime.now(IST)

        # ---- Parse Entry Time ----
        if isinstance(entry_time_val, str):
            try:
                entry_time = datetime.strptime(entry_time_val, "%Y-%m-%d %H:%M:%S")
                entry_time = IST.localize(entry_time)
            except ValueError:
                h, m, s = map(int, entry_time_val.split(":"))
                entry_time = now.replace(hour=h, minute=m, second=s, microsecond=0)
        else:
            entry_time = entry_time_val
            if entry_time.tzinfo is None:
                entry_time = IST.localize(entry_time)

        # ---- Time Difference ----
        elapsed_secs = max((now - entry_time).total_seconds(), 0)

        # ---- Apply decay ONLY for options ----
        if "CE" in symbol or "PE" in symbol:

            per_sec_inc = get_dynamic_increment(elapsed_secs)
            decrement = elapsed_secs * per_sec_inc

            dynamic_val = original_price - decrement
        else:
            dynamic_val = original_price

        return round(dynamic_val, 2)

    except Exception as e:
        print(f"[ERROR] dynamic_entry: {e}")
        return original_price
