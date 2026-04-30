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
    except:
        return d

def i(x, d=0):
    try:
        return int(float(x))
    except:
        return d

def target_price(row):
    try:
        # 1. DATA FETCH
        entry_prc = i(row.get("pxy_entry") or row.get("buy_prc"))
        if entry_prc <= 0:
            return 0

        atr = f(row.get("atr"), 0.0)
        ce_p, ce_f = f(row.get("ce_power"), 0.0), f(row.get("ce_force"), 0.0)
        pe_p, pe_f = f(row.get("pe_power"), 0.0), f(row.get("pe_force"), 0.0)
        
        ce_depth = f(row.get("hkin_ce_depth"), 0.0)
        pe_depth = f(row.get("hkin_pe_depth"), 0.0)
        
        symbol = str(row.get("symbol", "UNKNOWN")).upper()
        is_ce, is_pe = "CE" in symbol, "PE" in symbol

        # SIGNALS
        exit_sig = str(row.get("exit", "NONE")).upper()
        st_sig = str(row.get("supertrend", "NONE")).upper()

        # --- TIME CALCULATIONS ---
        now = datetime.now(IST)
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

        # 2. 🎯 DYNAMIC TARGET LOGIC
        score = 1.4  # Default percentage for Status Quo
        state = "⏳" # Status Quo
        active_depth = 0.0

        if is_ce:
            active_depth = ce_depth
            # CE Surgical: ST UP/BUY and Exit BUY/BULL
            if any(x in st_sig for x in ["UP", "BUY"]) and any(x in exit_sig for x in ["BUY", "BULL"]):
                # SURGICAL FIX: score = ATR * Power(min 1) * Force(min 1)
                score = atr * max(1.0, ce_p) * max(1.0, ce_f / 10)
                state = "🔥"

        elif is_pe:
            active_depth = pe_depth
            # PE Surgical: ST DOWN/SELL and Exit SELL/BEAR
            if any(x in st_sig for x in ["DOWN", "SELL"]) and any(x in exit_sig for x in ["SELL", "BEAR"]):
                # SURGICAL FIX: score = ATR * Power(min 1) * Force(min 1)
                score = atr * max(1.0, pe_p) * max(1.0, pe_f / 10)
                state = "🔥"

        # 4. FINAL CALCULATION
        if state == "🔥":
            # ATR surgical target: Entry + Score Points + Depth
            target = int(entry_prc + score + active_depth)
        else:
            # Status Quo target: Entry + 1.4%
            target = int(entry_prc * (1 + 1.4 / 100))

        # CLEAN OUTPUT
        if DEBUG_MODE:
            clean_symbol = symbol.split('26', 1)[-1] if '26' in symbol else symbol
            status_msg = " [NEW]" if elapsed_secs <= 180 else f" [{int(elapsed_secs/60)}m]"
            # In Status Quo, we print 1.4 as the score; in Surgical, we print the ATR-based points
            print(f"{clean_symbol}|| E:{entry_prc}|| S:{score:.1f}|| {state} || T:{target}{status_msg}")

        return target

    except Exception as e:
        print(f"ERROR|{str(e)}")
        return 0


