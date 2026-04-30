from datetime import time, datetime
import pytz
from colorama import init, Fore

init(autoreset=True)
IST = pytz.timezone("Asia/Kolkata")

# --- DEBUG CONFIG ---
DEBUG_MODE = True 

def f(x, d=0.0):
    try:
        val = float(x)
        return val if val > 0 else d
    except: return d

def i(x, d=0):
    try: return int(float(x))
    except: return d

def target_price(row):
    try:
        # 1. DATA FETCH
        entry_prc = i(row.get("pxy_entry") or row.get("buy_prc"))
        if entry_prc <= 0: return 0

        atr = f(row.get("atr"), 0.0)
        ce_p, ce_f = f(row.get("ce_power"), 0.0), f(row.get("ce_force"), 0.0)
        pe_p, pe_f = f(row.get("pe_power"), 0.0), f(row.get("pe_force"), 0.0)
        
        # FIXED: Mapped to your log field names
        ce_depth = f(row.get("hkin_ce_depth"), 0.0)
        pe_depth = f(row.get("hkin_pe_depth"), 0.0)

        symbol = str(row.get("symbol", "UNKNOWN")).upper()
        is_ce, is_pe = "CE" in symbol, "PE" in symbol

        # SIGNALS
        exit_sig = str(row.get("exit", "NONE")).upper()
        st_sig = str(row.get("supertrend", "NONE")).upper()

        # --- DEBUG PRINT ---
        if DEBUG_MODE:
            print(f"{Fore.CYAN}DEBUG DATA | {symbol} | E:{entry_prc} | ATR:{atr} | CP:{ce_p} | CF:{ce_f} | CD:{ce_depth} | ST:{st_sig} | EX:{exit_sig}")

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
                    try:
                        parts = list(map(int, entry_time_val.split(":")))
                        e_time = now.replace(hour=parts[0], minute=parts[1], second=parts[2] if len(parts)>2 else 0, microsecond=0)
                    except: e_time = now
            else:
                e_time = entry_time_val if entry_time_val.tzinfo else IST.localize(entry_time_val)
            elapsed_secs = (now - e_time).total_seconds()

        # 2. 🚨 THE MASTER KILL-SWITCH (ST SIGNAL ONLY)
        is_fresh = elapsed_secs <= 180 and not is_morning
        
        if not is_fresh and not is_morning:
            if is_ce and any(x in st_sig for x in ["DOWN", "SELL"]):
                print(f"{symbol}|| 🛑 ST_KILL_CE (OLD) || T:0")
                return 0
            if is_pe and any(x in st_sig for x in ["UP", "BUY"]):
                print(f"{symbol}|| 🛑 ST_KILL_PE (OLD) || T:0")
                return 0

        # 3. 🎯 DYNAMIC TARGET LOGIC
        score = 1.4 
        state = "✅"
        active_depth = 0.0

        if is_ce:
            active_depth = ce_depth
            if any(x in exit_sig for x in ["BUY", "BULL"]) and "SELL" not in exit_sig:
                # SURGICAL SCORE = 1.4 * Power * Force
                score = atr * ce_p 
                state = "🔥" if score > 0 else "⚠️"
            else:
                score, state = 1.4, "⏳" if is_fresh else "❌"
        
        elif is_pe:
            active_depth = pe_depth
            if any(x in exit_sig for x in ["SELL", "BEAR"]) and "BUY" not in exit_sig:
                # SURGICAL SCORE = 1.4 * Power * Force
                score = atr * pe_p 
                state = "🔥" if score > 0 else "⚠️"
            else:
                score, state = 1.4, "⏳" if is_fresh else "❌"

        # 4. FINAL CALCULATION (Exact Request: ATR*P*F + DEPTH)
        if state == "🔥" and active_depth > 0:
            target = int(score + active_depth)
        else:
            target = int(entry_prc * (1 + score / 100))

        # CLEAN OUTPUT
        clean_symbol = symbol.split('26', 1)[-1] if '26' in symbol else symbol
        status_msg = " [NEW]" if is_fresh else f" [{int(elapsed_secs/60)}m]"
        print(f"{clean_symbol}|| E:{entry_prc:03d}|| D:{active_depth:.1f}|| S:{score:.2f}|| {state} || T:{target:03d}{status_msg}")
        
        return target

    except Exception as e:
        print(f"ERROR|{str(e)}")
        return 0


