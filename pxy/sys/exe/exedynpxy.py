from datetime import datetime

def dynamic_entry(row):
    """
    Calculate a dynamic entry price based on elapsed time since buy.
    Increment: 1 point per minute.
    Works for CE/PE options only.
    """
    try:
        original_price = float(row.get("buy_prc", 0))
        entry_time_val = row.get("buy_time")  # match your OMS column
        symbol = str(row.get("symbol", "")).upper()

        if not entry_time_val or original_price == 0:
            return original_price

        now = datetime.now()

        # --- Parse full datetime if possible ---
        if isinstance(entry_time_val, str):
            try:
                # expected format: "YYYY-MM-DD HH:MM:SS"
                entry_time = datetime.strptime(entry_time_val, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                # fallback for only HH:MM:SS
                entry_time = datetime.strptime(entry_time_val, "%H:%M:%S").replace(
                    year=now.year, month=now.month, day=now.day
                )
        else:
            entry_time = entry_time_val  # already a datetime object

        # --- elapsed seconds ---
        elapsed_secs = (now - entry_time).total_seconds()
        if elapsed_secs < 0:
            elapsed_secs = 0  # prevent negative increment

        # --- increment 1 point per minute → 1/60 point per second ---
        increment = elapsed_secs / 60.0

        # --- only for CE/PE options ---
        dynamic_val = original_price + increment if ("CE" in symbol or "PE" in symbol) else original_price

        return round(dynamic_val, 2)

    except Exception as e:
        print(f"[ERROR] dynamic_entry: {e}")
        return original_price
