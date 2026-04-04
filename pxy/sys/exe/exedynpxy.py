from datetime import datetime

def dynamic_entry(row):
    try:
        original_price = float(row.get("buy_prc", 0))
        current_price = float(row.get("ltp", row.get("sell_prc", 0)))
        entry_time_val = row.get("entry_time")
        symbol = str(row.get("symbol", "")).upper()

        if not entry_time_val or original_price == 0:
            return original_price

        now = datetime.now()
        if isinstance(entry_time_val, str):
            entry_time = datetime.strptime(entry_time_val, "%H:%M:%S").replace(
                year=now.year, month=now.month, day=now.day
            )
        else:
            entry_time = entry_time_val

        elapsed_mins = (now - entry_time).total_seconds() / 60
        decay = round(elapsed_mins * 0.20, 2)

        # Theta decay
        dynamic_val = original_price - decay if ("CE" in symbol or "PE" in symbol) else original_price

        # --- ONLY FOR LOSING TRADES (> ₹10 LOSS) ---
        if current_price > 0 and original_price > current_price:
            loss = original_price - current_price

            if loss > 10:   # 👈 changed from 15 → 10
                return round(max((dynamic_val * 0.4 + current_price * 0.6), 2.0), 2)

        # --- DEFAULT ---
        return round(max(dynamic_val, 2.0), 2)

    except Exception:
        return row.get("buy_prc", 0)

