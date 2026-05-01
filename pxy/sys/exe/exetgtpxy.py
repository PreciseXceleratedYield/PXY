# tgtpxy.py
import pytz
from datetime import datetime
from colorama import init, Fore, Style

init(autoreset=True)
IST = pytz.timezone("Asia/Kolkata")

# --- CONFIG ---
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
        # 1. DATA EXTRACTION
        entry_prc = i(row.get("pxy_entry") or row.get("buy_prc"))
        if entry_prc <= 0: return 0
        
        atr = f(row.get("atr"), 0.0)
        ce_p = f(row.get("ce_power"), 0.0)
        pe_p = f(row.get("pe_power"), 0.0)
        symbol = str(row.get("symbol", "UNKNOWN")).upper()
        is_ce, is_pe = "CE" in symbol, "PE" in symbol
        
        # PXY® Signal Parsing
        st_sig = str(row.get("supertrend", "NONE")).upper()
        exit_sig = str(row.get("exit", "NONE")).upper()

        # 2. TIME CLASSIFICATION (1-Minute Rule)
        now = datetime.now(IST)
        entry_time_val = row.get("buy_time")
        elapsed_secs = 0
        if entry_time_val:
            if isinstance(entry_time_val, str):
                try: 
                    e_time = datetime.strptime(entry_time_val, "%Y-%m-%d %H:%M:%S")
                    e_time = IST.localize(e_time)
                except: e_time = now
            else: 
                e_time = entry_time_val if entry_time_val.tzinfo else IST.localize(entry_time_val)
            elapsed_secs = (now - e_time).total_seconds()

        is_new = elapsed_secs < 60  # Rule 1: < 1 min is New
        
        # 3. SCORE CONSTANTS
        min_profit_pct = 1.4
        fallback_score = int(entry_prc * (min_profit_pct / 100))
        
        state = "⏳" # Default: Survival
        score = fallback_score

        # Precise Signal Mapping
        st_is_up = any(x in st_sig for x in ["UP", "BUY", "STBUY", "ATMBUY"])
        st_is_down = any(x in st_sig for x in ["DOWN", "SELL", "STSELL", "ATMSELL"])
        st_is_neutral = any(x in st_sig for x in ["SIDE", "NONE"])
        
        exit_is_bull = any(x in exit_sig for x in ["BUY", "BULL"])
        exit_is_bear = any(x in exit_sig for x in ["SELL", "BEAR"])

        # 4. SURGICAL LOGIC EXECUTION
        if is_ce:
            if is_new:
                # Rule: New entries follow Exit Signal
                if exit_is_bull: 
                    state, score = "🔥", max(fallback_score, (atr * max(1.0, ce_p)))
                else: 
                    state = "⏳"
            else:
                # Rule: Old entries subject to PXY® Filters
                if st_is_down and exit_is_bear: 
                    state = "💀" # Immediate Market Exit
                elif (st_is_up or st_is_neutral) and exit_is_bull: 
                    state, score = "🔥", max(fallback_score, (atr * max(1.0, ce_p)))
                else: 
                    state = "⏳"

        elif is_pe:
            if is_new:
                # Rule: New entries follow Exit Signal
                if exit_is_bear: 
                    state, score = "🔥", max(fallback_score, (atr * max(1.0, pe_p)))
                else: 
                    state = "⏳"
            else:
                # Rule: Old entries subject to PXY® Filters
                if st_is_up and exit_is_bull: 
                    state = "💀" # Immediate Market Exit
                elif (st_is_down or st_is_neutral) and exit_is_bear: 
                    state, score = "🔥", max(fallback_score, (atr * max(1.0, pe_p)))
                else: 
                    state = "⏳"

        # 5. FINAL TARGET CALCULATION
        if state == "🔥":
            target = int(entry_prc + score)
        elif state == "💀":
            target = -1
        else:
            target = int(entry_prc + fallback_score)

        # 6. TERMINAL REPORTING
        if DEBUG_MODE:
            clean_symbol = symbol.split('26', 1)[-1] if '26' in symbol else symbol
            color = Fore.RED if state == "💀" else (Fore.GREEN if state == "🔥" else Fore.YELLOW)
            status = "NEW" if is_new else f"OLD:{int(elapsed_secs/60)}m"
            print(f"{color}{clean_symbol}|| ST:{st_sig} || {state} || TGT:{int(target)} || {status}{Style.RESET_ALL}")

        return target
    except Exception as e:
        if DEBUG_MODE: print(f"ERROR|{str(e)}")
        return 0

