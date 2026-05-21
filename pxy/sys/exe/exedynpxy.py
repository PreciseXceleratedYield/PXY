# sys/exe/dynentrypxy.py
from datetime import datetime
import pytz
import re
import pandas as pd

IST = pytz.timezone("Asia/Kolkata")

# ==================================================
# 🔧 REVISED CONFIG: COMPRESSION DETECTOR TIME DECAY
# ==================================================
BASE_DECAY_RATE = 0.0005
PNL_THRESHOLD = 0.0
GRACE_WINDOW_SECS = 1800  # 30 minutes grace window in seconds

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
        elapsed_secs = max((now - entry_time).total_seconds(), 0)

        # ---------------- DUAL-PHASE DECAY SYSTEM ----------------
        if elapsed_secs <= GRACE_WINDOW_SECS:
            # Phase 1: Flat baseline decay time loop
            active_decay_rate = BASE_DECAY_RATE
            phase_tag = "EARLY ROOM (1.0x)"
        else:
            # Phase 2: After 30 minutes, evaluate compression state triggers
            ce_depth = float(row.get("hkin_ce_depth", 1.0))
            pe_depth = float(row.get("hkin_pe_depth", 1.0))
            past_depth_str = str(row.get("hkin_past_depth", "NA")).upper().strip()
            
            # CRITICAL TRIGGER SQUEEZE CONDITION: Run past depth ONLY when both are 1
            if ce_depth == 1.0 and pe_depth == 1.0:
                if "CE" in symbol and "CE" in past_depth_str:
                    match = re.search(r'CE(\d+)', past_depth_str)
                    depth = float(match.group(1)) if match else 1.0
                elif "PE" in symbol and "PE" in past_depth_str:
                    match = re.search(r'PE(\d+)', past_depth_str)
                    depth = float(match.group(1)) if match else 1.0
                else:
                    depth = 1.0
                phase_tag = f"SQUEEZE PAST ACCEL ({depth:.1f}x)"
            else:
                # MODIFIED FALLBACK: No standard depth penalty allowed. Defaults strictly to pure time decay.
                depth = 1.0
                phase_tag = "(1.0x)"

            # Protect against negative depth adjustments or zero values safely
            if depth <= 0:
                depth = 1.0

            active_decay_rate = BASE_DECAY_RATE * depth

        # ---------------- PURE DECAY RULE ----------------
        if pnl <= PNL_THRESHOLD:
            decay_amount = elapsed_secs * active_decay_rate
            dynamic_val = original_price - decay_amount
            clean_symbol = re.sub(r'^(NIFTY|BANKNIFTY)26', '', symbol)
            
            if decay_amount > 0.5:
                print(f"{clean_symbol} | {phase_tag} DECAY: -{decay_amount:.2f} PTS")
        else:
            dynamic_val = original_price
            
        return round(dynamic_val, 2)
        
    except Exception as e:
        return original_price



