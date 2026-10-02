# sys/exe/dynentrypxy.py
from datetime import datetime
import pytz
import re
import pandas as pd

IST = pytz.timezone("Asia/Kolkata")

# ==================================================
# 🔧 REVISED CONFIG: COMPRESSION DETECTOR TIME DECAY
# ==================================================
DECAY_RATE_PER_MIN = 0.0001  # 0.05% decay per minute (0.05 / 100)
PNL_THRESHOLD = 0.0

# Tracks the single worst/oldest trade separately for CE and PE (using minutes)
_worst_trades = {
    "CE": {"elapsed_mins": -1.0, "message": None},
    "PE": {"elapsed_mins": -1.0, "message": None}
}

def dynamic_entry(row):
    global _worst_trades
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
                entry_time = datetime.strptime(entry_time_val, "%Y-%m-%d %H:%M:%S")
                entry_time = IST.localize(entry_time)
            except:
                parts = list(map(int, str(entry_time_val).split(":")[-3:]))
                entry_time = now.replace(hour=parts[0], minute=parts[1], second=parts[2], microsecond=0)
        else:
            entry_time = pd.to_datetime(entry_time_val)
            if entry_time.tzinfo is None:
                entry_time = IST.localize(entry_time)
            else:
                entry_time = entry_time.astimezone(IST)

        # ---------------- CALC ELAPSED MINUTES ----------------
        elapsed_secs = max((now - entry_time).total_seconds(), 0)
        elapsed_mins = elapsed_secs / 60.0 

        # ---------------- PERCENTAGE DECAY RULE ----------------
        if pnl <= PNL_THRESHOLD:
            total_decay_percentage = elapsed_mins * DECAY_RATE_PER_MIN
            dynamic_val = original_price * (1.0 - total_decay_percentage)
            dynamic_val = max(dynamic_val, 0.0)
            
            decay_amount = original_price - dynamic_val
            pct_given_away = total_decay_percentage * 100.0
            
            # Determine Option Type
            opt_type = None
            if symbol.endswith("CE"):
                opt_type = "CE"
            elif symbol.endswith("PE"):
                opt_type = "PE"
                
            # Track worst trade independently for CE and PE if type is identified
            if opt_type and decay_amount > 0.05 and elapsed_mins > _worst_trades[opt_type]["elapsed_mins"]:
                clean_symbol = re.sub(r'^NIFTY26', '', symbol)
                _worst_trades[opt_type]["elapsed_mins"] = elapsed_mins
                _worst_trades[opt_type]["message"] = (
                    f"WORST {opt_type} | {clean_symbol} | "
                    f"GAVE AWAY: {pct_given_away:.2f}% (-{decay_amount:.2f} PTS) | "
                    f"ELAPSED: {elapsed_mins:.2f} mins"
                )
        else:
            dynamic_val = original_price
            
        return round(dynamic_val, 2)
        
    except Exception as e:
        print(f"Error in dynamic_entry: {e}")
        return original_price

def print_oldest_decay():
    """Prints the worst decayed CE and PE trades, then flushes runtime memory."""
    global _worst_trades
    
    # Print CE if recorded
    if _worst_trades["CE"]["message"] is not None:
        print(_worst_trades["CE"]["message"])
        
    # Print PE if recorded
    if _worst_trades["PE"]["message"] is not None:
        print(_worst_trades["PE"]["message"])
        
    # Reset internal memory block
    _worst_trades = {
        "CE": {"elapsed_mins": -1.0, "message": None},
        "PE": {"elapsed_mins": -1.0, "message": None}
    }
