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
        entry_prc = i(row.get("pxy_entry") or row.get("buy_prc"))
        if entry_prc <= 0: return 0

        symbol = str(row.get("symbol", "UNKNOWN")).upper()
        
        # --- SIGNAL SOURCE CHANGE: NOW USING 'EXIT' COLUMN ---
        sig = str(row.get("exit", "NONE")).upper() 
        
        is_ce, is_pe = "CE" in symbol, "PE" in symbol

        # --- TIME CALCULATIONS ---
        now = datetime.now(IST)
        is_morning = time(9, 15) <= now.time() < time(9, 30)

        entry_time_val = row.get("buy_time")
        elapsed_secs = 0
        if entry_time_val:
            if isinstance(entry_time_val, str):
                try:
                    e_time = datetime.strptime(entry_time_val, "%Y-%m-%d %H:%M:%S")
                    e_time = IST.localize(e_time)
                except:
                    parts = list(map(int, entry_time_val.split(":")))
                    e_time = now.replace(hour=parts[0], minute=parts[1], 
                                         second=parts[2] if len(parts)>2 else 0)
            else:
                e_time = entry_time_val if entry_time_val.tzinfo else IST.localize(entry_time_val)
            
            elapsed_secs = (now - e_time).total_seconds()

        # 2. 🚨 THE MASTER KILL-SWITCH (STRICT GATE)
        # Using the EXIT signal to determine if we should stay in
        if not is_morning and elapsed_secs > 120:
            # If trend is Bearish (SELL/DOWN) -> Kill CE
            if is_ce and any(x in sig for x in ["SELL", "DOWN"]):
                print(f"{symbol}|| 🛑 EXIT_SIG_BEARISH || T:0")
                return 0
            # If trend is Bullish (BUY/UP) -> Kill PE
            if is_pe and any(x in sig for x in ["BUY", "UP"]):
                print(f"{symbol}|| 🛑 EXIT_SIG_BULLISH || T:0")
                return 0

        # 3. 🎯 DYNAMIC TARGET LOGIC (RELAXED)
        is_fresh = elapsed_secs <= 120 and not is_morning

        if is_ce:
            # If trend is Bullish (BUY or UP)
            if any(x in sig for x in ["BUY", "UP"]):
                score = 20.0 if "BUY" in sig else 1.4
                state = "🔥" if "BUY" in sig else "✅"
            else:
                # Buffer period or neutral
                score, state = 1.4, "⏳" if is_fresh else "❌"
        
        elif is_pe:
            # If trend is Bearish (SELL or DOWN)
            if any(x in sig for x in ["SELL", "DOWN"]):
                score = 20.0 if "SELL" in sig else 1.4
                state = "🔥" if "SELL" in sig else "✅"
            else:
                score, state = 1.4, "⏳" if is_fresh else "❌"
        
        else:
            score, state = 1.4, "⚪"

        target = int(entry_prc * (1 + score / 100))

        # 4. CLEAN OUTPUT
        clean_symbol = symbol.split('26', 1)[-1] if '26' in symbol else symbol
        status_msg = f" [NEW_ENTRY]" if is_fresh else ""
        print(f"{clean_symbol}|| E:{entry_prc:03d}|| S:{score:.1f}%|| {state} || T:{target:03d}{status_msg}")
        
        return target

    except Exception as e:
        print(f"ERROR|{str(e)}")
        return 0



