import pytz
from datetime import datetime
from colorama import init, Fore, Style

init(autoreset=True)
IST = pytz.timezone("Asia/Kolkata")

# --- CONFIG ---
DEBUG_MODE = True
VERBOSE_DEBUG = True 

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
        ce_p = f(row.get("ce_power"), 0.0)
        pe_p = f(row.get("pe_power"), 0.0)
        symbol = str(row.get("symbol", "UNKNOWN")).upper()
        is_ce, is_pe = "CE" in symbol, "PE" in symbol
        
        # Signal values: SELL/BUY/UP/DOWN/BULL/BEAR/NONE
        st_sig = str(row.get("supertrend", "NONE")).upper()
        exit_sig = str(row.get("exit", "NONE")).upper()

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
                        e_time = now.replace(hour=parts[0], minute=parts[1], second=parts[2] if len(parts)>2 else 0)
                    except: e_time = now
            else:
                e_time = entry_time_val if entry_time_val.tzinfo else IST.localize(entry_time_val)
            elapsed_secs = (now - e_time).total_seconds()

        # 2. 🎯 LOGIC CONSTANTS
        is_new = elapsed_secs <= 120 # 2 min grace
        min_profit_pct = 1.4
        fallback_score = int(entry_prc * (min_profit_pct / 100))
        
        score = fallback_score
        state = "⏳"

        # Signal Mapping
        st_is_up = any(x in st_sig for x in ["UP", "BUY"])
        st_is_down = any(x in st_sig for x in ["DOWN", "SELL"])
        exit_is_bull = any(x in exit_sig for x in ["BUY", "BULL"])
        exit_is_bear = any(x in exit_sig for x in ["SELL", "BEAR"])

        # 3. 🛡️ CE / PE LOGIC
        if is_ce:
            if is_new:
                # Rule 2: New entries purely on matching exit signal
                if exit_is_bull:
                    score = max(fallback_score, (atr * max(1.0, ce_p)))
                    state = "🔥"
            else:
                # Rule 1: Old entries
                if st_is_down and exit_is_bear: 
                    state = "💀" # BOTH OPPOSITE -> KILL (-1)
                elif st_is_down and not exit_is_bull:
                    state = "⏳" # TREND OPPOSITE -> SURVIVE 1.4%
                elif (st_is_up or "NONE" in st_sig) and exit_is_bull:
                    score = max(fallback_score, (atr * max(1.0, ce_p)))
                    state = "🔥"
                else: 
                    state = "⏳" # Rule 3: Fallback 1.4%

        elif is_pe:
            if is_new:
                # Rule 2: New entries purely on matching exit signal
                if exit_is_bear:
                    score = max(fallback_score, (atr * max(1.0, pe_p)))
                    state = "🔥"
            else:
                # Rule 1: Old entries
                if st_is_up and exit_is_bull: 
                    state = "💀" # BOTH OPPOSITE -> KILL (-1)
                elif st_is_up and not exit_is_bear:
                    state = "⏳" # TREND OPPOSITE -> SURVIVE 1.4%
                elif (st_is_down or "NONE" in st_sig) and exit_is_bear:
                    score = max(fallback_score, (atr * max(1.0, pe_p)))
                    state = "🔥"
                else: 
                    state = "⏳" # Rule 3: Fallback 1.4%

        # 4. FINAL CALCULATION
        if state == "🔥":
            target = int(entry_prc + score)
        elif state == "💀":
            target = -1 # Immediate market exit trigger
        else:
            target = int(entry_prc + fallback_score)

        # CLEAN OUTPUT
        if DEBUG_MODE:
            clean_symbol = symbol.split('26', 1)[-1] if '26' in symbol else symbol
            color = Fore.RED if state == "💀" else (Fore.GREEN if state == "🔥" else Fore.YELLOW)
            msg = f" [NEW:{int(elapsed_secs)}s]" if is_new else f" [OLD:{int(elapsed_secs/60)}m]"
            print(f"{color}{clean_symbol}|| S:{score:.1f}|| {state} || TGT:{int(target)}{msg}{Style.RESET_ALL}")
            if VERBOSE_DEBUG:
                print(f"   [DEBUG] ST:{st_sig} | EXIT:{exit_sig} | Entry:{entry_prc}")

        return target

    except Exception as e:
        print(f"ERROR|{str(e)}")
        return 0



