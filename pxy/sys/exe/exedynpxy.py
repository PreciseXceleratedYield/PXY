from datetime import datetime
import pytz

IST = pytz.timezone("Asia/Kolkata")

def dynamic_entry(row):
    try:
        original_price = float(row.get("buy_prc", 0))
        entry_time_val = row.get("buy_time")  # OMS column
        symbol = str(row.get("symbol", "")).upper()

        if not entry_time_val or original_price == 0:
            return original_price

        # Current time in IST
        now = datetime.now(IST)

        # --- Parse entry time as IST ---
        if isinstance(entry_time_val, str):
            try:
                entry_time = datetime.strptime(entry_time_val, "%Y-%m-%d %H:%M:%S")
                entry_time = IST.localize(entry_time)
            except ValueError:
                # fallback: HH:MM:SS today
                h, m, s = map(int, entry_time_val.split(":"))
                entry_time = now.replace(hour=h, minute=m, second=s, microsecond=0)
        else:
            entry_time = entry_time_val
            if entry_time.tzinfo is None:
                entry_time = IST.localize(entry_time)

        # --- elapsed seconds ---
        elapsed_secs = (now - entry_time).total_seconds()
        elapsed_secs = max(elapsed_secs, 0)  # prevent negatives

        # --- increment: 1 point per minute ---
        increment = elapsed_secs / 60.0
        dynamic_val = original_price + increment if ("CE" in symbol or "PE" in symbol) else original_price

        return round(dynamic_val, 2)

    except Exception as e:
        print(f"[ERROR] dynamic_entry: {e}")
        return original_price
