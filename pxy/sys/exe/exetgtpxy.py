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
    except:
        return d

def i(x, d=0):
    try:
        return int(float(x))
    except:
        return d

def target_price(row):
    try:
        # 1. FIELD DEFINITIONS (Metrics > 1.0)
        hce_d = f(row.get("hkin_ce_depth"), 1.0)
        hpe_d = f(row.get("hkin_pe_depth"), 1.0)
        ce_p  = f(row.get("ce_power"), 1.0)
        pe_p  = f(row.get("pe_power"), 1.0)
        ce_f  = f(row.get("ce_force"), 1.0)
        pe_f  = f(row.get("pe_force"), 1.0)
        atr   = f(row.get("atr"), 0.0)

        # Basic Entry Data
        entry_prc = i(row.get("pxy_entry") or row.get("buy_prc"))
        if entry_prc <= 0:
            return 0
            
        symbol = str(row.get("symbol", "UNKNOWN")).upper()
        is_ce, is_pe = "CE" in symbol, "PE" in symbol
        
        # Signals & Counter Logic
        exit_sig = str(row.get("exit", "NONE")).upper()     # Fast Signal
        entry_sig = str(row.get("entry", "NONE")).upper()   # Main Trend Signal
        is_counter = str(row.get("counter", "N")).upper() == "Y"
        
        # 2. DYNAMIC SIGNAL SELECTION
        # Use Entry Signal for Counter trades, Exit Signal for Normal trades
        active_signal = entry_sig if is_counter else exit_sig

        # 3. FALLBACK CALC (1.4%)
        min_profit_pct = 1.4
        fallback_score = int(entry_prc * (min_profit_pct / 100))
        
        state = "⏳"
        score = fallback_score

        # 4. TARGET CALCULATION: atr * depth * force * power
        if is_ce:
            if "SELL" in active_signal:
                # Scaled target for CE
                calc_score = atr * hce_d * ce_f * ce_p
                state, score = "🔥", max(fallback_score, calc_score)
            else:
                state = "⏳"

        elif is_pe:
            if "BUY" in active_signal:
                # Scaled target for PE
                calc_score = atr * hpe_d * pe_f * pe_p
                state, score = "🔥", max(fallback_score, calc_score)
            else:
                state = "⏳"

        # 5. FINAL OUTPUT
        target = int(entry_prc + score)

        # 6. DEBUG PRINT
        if DEBUG_MODE:
            clean_symbol = symbol.split('26', 1)[-1] if '26' in symbol else symbol
            color = Fore.CYAN if state == "🔥" else (Fore.MAGENTA if is_counter else Fore.YELLOW)
            mode = "COUNTER" if is_counter else "FAST"
            print(f"{color}{clean_symbol} | {mode} | SIG:{active_signal} | ST:{state} | TGT:{target}")

        return target

    except Exception as e:
        print(f"{Fore.RED}CRITICAL ERROR: {str(e)}{Style.RESET_ALL}")
        return 0


