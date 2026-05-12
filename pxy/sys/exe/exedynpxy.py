# sys/exe/dynentrypxy.py
from datetime import datetime
import pytz
import re

IST = pytz.timezone("Asia/Kolkata")

# ==================================================
# 🔧 TIGHTENED CONFIG: PURE TIME DECAY
# ==================================================
# 0.005 per second = 0.3 points per minute = 18 points per hour
BASE_DECAY_RATE = 0.0001
PNL_THRESHOLD = 0.0

def dynamic_entry(row):
    try:
        original_price = float(row.get("buy_prc", 0))
        entry_time_val = row.get("buy_time")
        symbol = str(row.get("symbol", "")).upper()
        pnl = float(row.get("pnl", 0))

        if not entry_time_val or original_price <= 0:
            return original_price

        now = datetime.now(IST)

        # ---------------- PARSE ENTRY TIME ----------------
        if isinstance(entry_time_val, str):
            try:
                # Expecting "YYYY-MM-DD HH:MM:SS"
                entry_time = datetime.strptime(entry_time_val, "%Y-%m-%d %H:%M:%S")
                entry_time = IST.localize(entry_time)
            except ValueError:
                # Fallback for "HH:MM:S" format
                parts = list(map(int, entry_time_val.split(":")))
                while len(parts) < 3: parts.append(0)
                h, m, s = parts[:3]
                entry_time = now.replace(hour=h, minute=m, second=s, microsecond=0)
        else:
            entry_time = entry_time_val
            if entry_time.tzinfo is None:
                entry_time = IST.localize(entry_time)

        # ---------------- CALC ELAPSED ----------------
        elapsed_secs = max((now - entry_time).total_seconds(), 0)

        # ---------------- PURE DECAY RULE ----------------
        # If PNL is 0 or negative, start the linear decay
        if pnl <= PNL_THRESHOLD:
            decay_amount = elapsed_secs * BASE_DECAY_RATE
            dynamic_val = original_price - decay_amount
            
            # Clean symbol for logging
            clean_symbol = re.sub(r'^(NIFTY|BANKNIFTY)26', '', symbol)
            if decay_amount > 0.5: # Only print if meaningful decay
                print(f"{clean_symbol} | TIME DECAY: -{decay_amount:.2f} PTS")
        else:
            # If in profit, keep original buy price (don't decay)
            dynamic_val = original_price

        return round(dynamic_val, 2)

    except Exception as e:
        print(f"[ERROR] dynamic_entry: {e}")
        return original_price

