# sys/exe/dynentrypxy.py
from datetime import datetime
import pytz
import re
import pandas as pd

IST = pytz.timezone("Asia/Kolkata")

# ==================================================
# 🔧 TIGHTENED CONFIG: PURE TIME DECAY
# ==================================================
BASE_DECAY_RATE = 0.001 
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
                # Try full format
                entry_time = datetime.strptime(entry_time_val, "%Y-%m-%d %H:%M:%S")
                entry_time = IST.localize(entry_time)
            except:
                # Fallback for just time "HH:MM:SS"
                parts = list(map(int, str(entry_time_val).split(":")[-3:]))
                entry_time = now.replace(hour=parts[0], minute=parts[1], second=parts[2], microsecond=0)
        else:
            # Handle Numpy/Pandas types
            entry_time = pd.to_datetime(entry_time_val)
            
            # CRITICAL FIX: Ensure timezone awareness
            if entry_time.tzinfo is None:
                entry_time = IST.localize(entry_time)
            else:
                entry_time = entry_time.astimezone(IST)

        # ---------------- CALC ELAPSED ----------------
        # Both 'now' and 'entry_time' are now IST aware
        elapsed_secs = max((now - entry_time).total_seconds(), 0)

        # ---------------- PURE DECAY RULE ----------------
        if pnl <= PNL_THRESHOLD:
            decay_amount = elapsed_secs * BASE_DECAY_RATE
            dynamic_val = original_price - decay_amount
            
            clean_symbol = re.sub(r'^(NIFTY|BANKNIFTY)26', '', symbol)
            if decay_amount > 0.5:
                print(f"{clean_symbol} | TIME DECAY: -{decay_amount:.2f} PTS")
        else:
            dynamic_val = original_price

        return round(dynamic_val, 2)

    except Exception as e:
        # If error occurs, return original price to avoid breaking the trade
        return original_price

