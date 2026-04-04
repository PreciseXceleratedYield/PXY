# sys/exe/exedynpxy.py
from datetime import datetime

def dynamic_entry(row):
    """
    Stateless 1-minute decay: 0.20 points per minute.
    - Baseline: buy_prc
    - Result: pxy_entry (used by TGT and SL modules)
    - Logic: Both CE and PE subtract decay (Time/Theta eats premium).
    """
    try:
        # 1. Get original buy price and entry time
        original_price = float(row.get("buy_prc", 0))
        entry_time_val = row.get("entry_time")
        symbol = str(row.get("symbol", "")).upper()

        # If data is missing or trade hasn't started, return original
        if not entry_time_val or original_price == 0:
            return original_price

        # 2. Parse Entry Time into datetime object
        now = datetime.now()
        if isinstance(entry_time_val, str):
            # Assumes format HH:MM:SS (e.g., 09:15:30)
            entry_time = datetime.strptime(entry_time_val, "%H:%M:%S").replace(
                year=now.year, month=now.month, day=now.day
            )
        else:
            entry_time = entry_time_val

        # 3. Calculate Elapsed Minutes & Decay
        elapsed_mins = (now - entry_time).total_seconds() / 60
        
        # Apply 0.20 points per minute adjustment (₹1.00 every 5 mins)
        decay = round(elapsed_mins * 0.20, 2)

        # 4. Calculate pxy_entry
        # Options lose value over time regardless of direction (Theta)
        if "CE" in symbol or "PE" in symbol:
            dynamic_val = original_price - decay
        else:
            dynamic_val = original_price

        # 5. Airtight Floor: Ensure price never goes below ₹2.00
        return round(max(dynamic_val, 2.0), 2)

    except Exception:
        # Fallback to original price on any error
        return row.get("buy_prc", 0)

