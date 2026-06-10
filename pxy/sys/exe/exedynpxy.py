# sys/exe/dynentrypxy.py
from datetime import datetime
import pytz
import re
import pandas as pd

IST = pytz.timezone("Asia/Kolkata")

# ==================================================
# 🔧 REVISED CONFIG: COMPRESSION DETECTOR TIME DECAY
# ==================================================
DECAY_RATE_PER_HOUR = 0.01  # 1% decay per hour
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

        # ---------------- CALC ELAPSED HOURS ----------------
        elapsed_secs = max((now - entry_time).total_seconds(), 0)
        elapsed_hours = elapsed_secs / 3600.0  # Convert to fractional hours

        # ---------------- PERCENTAGE DECAY RULE ----------------
        if pnl <= PNL_THRESHOLD:
            # Formula: Total % to decay = elapsed hours * 1%
            total_decay_percentage = elapsed_hours * DECAY_RATE_PER_HOUR
            
            # Calculate the final dynamic value after decay
            dynamic_val = original_price * (1.0 - total_decay_percentage)
            
            # Ensure price doesn't decay below zero
            dynamic_val = max(dynamic_val, 0.0)
            
            decay_amount = original_price - dynamic_val
            clean_symbol = re.sub(r'^(NIFTY|BANKNIFTY)26', '', symbol)
            
            if decay_amount > 0.05:
                print(f"{clean_symbol} | DECAY (1% / hr): -{decay_amount:.2f} PTS ({elapsed_hours:.2f} hrs elapsed)")
        else:
            dynamic_val = original_price
            
        return round(dynamic_val, 2)
        
    except Exception as e:
        print(f"Error in dynamic_entry: {e}")
        return original_price



