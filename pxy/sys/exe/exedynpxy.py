from datetime import datetime
import pytz
import re

IST = pytz.timezone("Asia/Kolkata")

BASE_INCREMENT = 0.001


def dynamic_entry(row):
    try:
        original_price = float(row.get("buy_prc", 0))
        entry_time_val = row.get("buy_time")
        symbol = str(row.get("symbol", "")).upper()
        supertrend = str(row.get("supertrend", "")).upper().strip()

        if not entry_time_val or original_price == 0:
            return original_price

        now = datetime.now(IST)

        is_ce = "CE" in symbol
        is_pe = "PE" in symbol

        # ==================================================
        # 🧠 TREND ALIGNMENT CHECK
        # ==================================================
        aligned = False

        if is_ce and supertrend == "UP":
            aligned = True

        if is_pe and supertrend == "DOWN":
            aligned = True

        # ==================================================
        # PARSE TIME
        # ==================================================
        if isinstance(entry_time_val, str):
            try:
                entry_time = datetime.strptime(entry_time_val, "%Y-%m-%d %H:%M:%S")
                entry_time = IST.localize(entry_time)
            except ValueError:
                parts = list(map(int, entry_time_val.split(":")))
                while len(parts) < 3:
                    parts.append(0)
                h, m, s = parts[:3]
                entry_time = now.replace(hour=h, minute=m, second=s, microsecond=0)
        else:
            entry_time = entry_time_val
            if entry_time.tzinfo is None:
                entry_time = IST.localize(entry_time)

        elapsed_secs = max((now - entry_time).total_seconds(), 0)

        # ==================================================
        # FINAL DECISION
        # ==================================================
        if is_ce or is_pe:

            if aligned:
                # 🟢 NO DECAY IN TREND DIRECTION
                return round(original_price, 2)

            else:
                # 🔴 DECAY ONLY WHEN AGAINST TREND
                increment = elapsed_secs * BASE_INCREMENT
                dynamic_val = original_price - increment

                print(f"{symbol} | AGAINST TREND DECAY: {int(increment)} pts")

                return round(dynamic_val, 2)

        return original_price

    except Exception as e:
        print(f"[ERROR] dynamic_entry: {e}")
        return original_price
