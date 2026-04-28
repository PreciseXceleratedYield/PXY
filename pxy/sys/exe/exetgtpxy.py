# sys/exe/exetgtpxy_dashboard.py
from datetime import time, datetime
import pytz
from colorama import init

init(autoreset=True)
IST = pytz.timezone("Asia/Kolkata")

def i(x, d=0):
    try: return int(float(x))
    except: return d

def target_price(row):
    try:
        # 1. DATA FETCH
        entry = i(row.get("pxy_entry") or row.get("buy_prc"))
        if entry <= 0: return 0

        symbol = str(row.get("symbol", "UNKNOWN")).upper()
        # sig = st_signal from your ST script (BUY, SELL, UP, DOWN)
        sig = str(row.get("entry", "NONE")).upper()
        is_ce, is_pe = "CE" in symbol, "PE" in symbol

        # --- TIME CALCULATIONS (Matching dynentrypxy logic) ---
        now = datetime.now(IST)
        is_morning = time(9, 15) <= now.time() < time(9, 30)

        entry_time_val = row.get("buy_time")
        elapsed_secs = 0
        if entry_time_val:
            if isinstance(entry_time_val, str):
                try:
                    # Match your "YYYY-MM-DD HH:MM:SS" format
                    e_time = datetime.strptime(entry_time_val, "%Y-%m-%d %H:%M:%S")
                    e_time = IST.localize(e_time)
                except:
                    # Fallback parser
                    parts = list(map(int, entry_time_val.split(":")))
                    e_time = now.replace(hour=parts[0], minute=parts[1], 
                                         second=parts[2] if len(parts)>2 else 0)
            else:
                e_time = entry_time_val if entry_time_val.tzinfo else IST.localize(entry_time_val)
            
            elapsed_secs = (now - e_time).total_seconds()

        # 2. 🚨 THE MASTER KILL-SWITCH (STRICT GATE)
        # Rule: Skip exit if trade is < 120s old to allow for entry instability
        if not is_morning and elapsed_secs > 120:
            if is_ce and any(x in sig for x in ["SELL", "DOWN"]):
                print(f"{symbol}|| 🛑 TREND_FLIP_EXIT || T:0")
                return 0
            if is_pe and any(x in sig for x in ["BUY", "UP"]):
                print(f"{symbol}|| 🛑 TREND_FLIP_EXIT || T:0")
                return 0

        # 3. 🎯 DYNAMIC TARGET LOGIC (RELAXED)
        is_fresh = elapsed_secs <= 120 and not is_morning

        if is_ce:
            if "BUY" in sig:
                score, state = 20.0, "🔥"
            else:
                # If fresh, use 1.4% and show '⏳' status
                score, state = 1.4, "⏳" if is_fresh else "✅"
        
        elif is_pe:
            if "SELL" in sig:
                score, state = 20.0, "🔥"
            else:
                score, state = 1.4, "⏳" if is_fresh else "✅"
        
        else:
            score, state = 1.4, "⚪"

        target = int(entry * (1 + score / 100))

        # 4. CLEAN OUTPUT
        clean_symbol = symbol.split('26', 1)[-1] if '26' in symbol else symbol
        status_msg = f" [BUFFER]" if is_fresh else ""
        print(f"{clean_symbol}|| E:{entry:03d}|| S:{score:.1f}%|| {state} || T:{target:03d}{status_msg}")
        
        return target

    except Exception as e:
        print(f"ERROR|{str(e)}")
        return 0


