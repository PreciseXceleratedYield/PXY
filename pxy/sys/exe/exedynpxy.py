from datetime import datetime
import pytz

IST = pytz.timezone("Asia/Kolkata")

# ---- GLOBAL FACTOR ----
PER_SECOND_INCREMENT = 0.01   # 0.01 increase every second

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

        # ---- Apply Increment ONLY for Options ----
        if "CE" in symbol or "PE" in symbol:
            increment = elapsed_secs * PER_SECOND_INCREMENT
            dynamic_val = original_price - increment
        else:
            dynamic_val = original_price

        return round(dynamic_val, 2)

    except Exception as e:
        print(f"[ERROR] dynamic_entry: {e}")
        return original_price
