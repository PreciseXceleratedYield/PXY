# exedynpxy.py
from datetime import datetime

def dynamic_entry(row):
    """
    Calculate a dynamic entry price based on elapsed time since buy.
    Increment: 1 point per minute.
    Works for CE/PE options only.
    Maintains baseline price from OMS and avoids negative increments.
    """
    try:
        # 1️⃣ Get original buy price
        original_price = float(row.get("buy_prc", 0))
        if original_price == 0:
            return 0.0

        # 2️⃣ Read buy_time column from OMS (lowercase after df.columns standardization)
        entry_time_val = row.get("buy_time")
        if not entry_time_val:
            return original_price

        symbol = str(row.get("symbol", "")).upper()

        # 3️⃣ Parse datetime
        now = datetime.now()
        if isinstance(entry_time_val, str):
            try:
                # Format: "YYYY-MM-DD HH:MM:SS"
                entry_time = datetime.strptime(entry_time_val, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                # fallback for HH:MM:SS only
                entry_time = datetime.strptime(entry_time_val, "%H:%M:%S").replace(
                    year=now.year, month=now.month, day=now.day
                )
        else:
            entry_time = entry_time_val  # already a datetime object

        # 4️⃣ Calculate elapsed seconds
        elapsed_secs = (now - entry_time).total_seconds()
        if elapsed_secs < 0:
            elapsed_secs = 0  # prevent negative increment

        # 5️⃣ Increment 1 point per minute
        increment = elapsed_secs / 60.0

        # 6️⃣ Apply only for CE/PE options
        if "CE" in symbol or "PE" in symbol:
            dynamic_val = original_price + increment
        else:
            dynamic_val = original_price

        # 7️⃣ Round to 2 decimals
        return round(dynamic_val, 2)

    except Exception as e:
        print(f"[ERROR] dynamic_entry: {e}")
        return original_price
