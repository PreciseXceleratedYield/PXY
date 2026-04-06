from datetime import datetime

def dynamic_entry(row):
    try:
        original_price = float(row.get("buy_prc", 0))
        entry_time_val = row.get("entry_time")
        symbol = str(row.get("symbol", "")).upper()

        if not entry_time_val or original_price == 0:
            return original_price

        now = datetime.now()
        # Convert entry_time string to datetime if needed
        if isinstance(entry_time_val, str):
            entry_time = datetime.strptime(entry_time_val, "%H:%M:%S").replace(
                year=now.year, month=now.month, day=now.day
            )
        else:
            entry_time = entry_time_val

        # --- elapsed seconds ---
        elapsed_secs = (now - entry_time).total_seconds()

        # --- increment 1 point per minute → 1/60 point per second ---
        increment = elapsed_secs / 60

        # --- only for CE/PE options ---
        dynamic_val = original_price + increment if ("CE" in symbol or "PE" in symbol) else original_price

        return round(dynamic_val, 2)

    except Exception:
        return row.get("buy_prc", 0)

