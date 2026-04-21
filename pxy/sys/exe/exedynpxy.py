from datetime import datetime
import pytz
import math
import re

IST = pytz.timezone("Asia/Kolkata")

# ==================================================
# 🔧 CONFIG (TUNE FROM HERE ONLY)
# ==================================================
BASE_INCREMENT = 0.0005
PNL_THRESHOLD = -300


def dynamic_entry(row):
    try:
        original_price = float(row.get("buy_prc", 0))
        entry_time_val = row.get("buy_time")
        symbol = str(row.get("symbol", "")).upper()
        pnl = float(row.get("pnl", 0))

        if not entry_time_val or original_price == 0:
            return original_price

        now = datetime.now(IST)

        # ---------------- SYMBOL TYPE ----------------
        is_ce = "CE" in symbol
        is_pe = "PE" in symbol

        # ---------------- DEPTH ----------------
        ce_depth = float(row.get("hkin_ce_depth", 1))
        pe_depth = float(row.get("hkin_pe_depth", 1))

        # ---------------- DEPTH FACTOR ----------------
        if is_ce:
            depth_factor = math.sqrt(max(ce_depth - 1, 0))
        elif is_pe:
            depth_factor = math.sqrt(max(pe_depth - 1, 0))
        else:
            depth_factor = 0

        per_second_increment = BASE_INCREMENT * depth_factor

        # ---------------- PARSE ENTRY TIME ----------------
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

        # ---------------- CLEAN SYMBOL ----------------
        clean_symbol = re.sub(r'^(NIFTY|BANKNIFTY)26', '', symbol)

        # ---------------- FINAL RULE ----------------
        if pnl <= PNL_THRESHOLD and (is_ce or is_pe):
            increment = elapsed_secs * per_second_increment
            dynamic_val = original_price - increment

            points = int(increment)
            print(f"{clean_symbol} | READY TO GIVEAWAY {points} POINTS")

        else:
            dynamic_val = original_price

        return round(dynamic_val, 2)

    except Exception as e:
        print(f"[ERROR] dynamic_entry: {e}")
        return original_price
