# tgtpxy.py
import pytz
from datetime import datetime
from colorama import init, Fore, Style

init(autoreset=True)
IST = pytz.timezone("Asia/Kolkata")

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
        # 1. DYNAMIC BASE (atr/3)
        atr_val = f(row.get("atr"), 9.0)
        BASE = atr_val 

        # 2. FIELD DEFINITIONS
        hce_d = f(row.get("hkin_ce_depth"), BASE)
        hpe_d = f(row.get("hkin_pe_depth"), BASE)
        ce_p  = f(row.get("ce_power"), BASE)
        pe_p  = f(row.get("pe_power"), BASE)
        ce_f  = f(row.get("ce_force"), BASE)
        pe_f  = f(row.get("pe_force"), BASE)

        # 3. ENTRY DATA
        entry_prc = i(row.get("pxy_entry") or row.get("buy_prc"))
        if entry_prc <= 0: return 0
            
        symbol = str(row.get("symbol", "UNKNOWN")).upper()
        is_ce, is_pe = "CE" in symbol, "PE" in symbol

        # 4. SIGNAL LOGIC (Always Exit Signal)
        active_signal = str(row.get("exit", "NONE")).upper()
        is_counter = str(row.get("counter", "N")).upper() == "Y"

        # 5. CALCULATION LOGIC (REFINED DIRECTION)
        floor_points = int(entry_prc * (BASE / 100))
        state = "⏳"
        score = floor_points

        # Define keyword groups
        bullish_triggers = ["BUY", "BULL", "OTMBUY", "ATMBUY"]
        bearish_triggers = ["SELL", "BEAR", "OTMSELL", "ATMSELL"]

        if is_ce:
            # CE goes UP on BULLISH signals
            if any(t in active_signal for t in bullish_triggers):
                calc_score = (BASE + ce_f + ce_p) / hce_d
                state, score = "🔥", max(floor_points, int(calc_score))
                
        elif is_pe:
            # PE goes UP on BEARISH signals
            if any(t in active_signal for t in bearish_triggers):
                calc_score = (BASE + pe_f + pe_p) / hpe_d 
                state, score = "🔥", max(floor_points, int(calc_score))

        # 6. FINAL OUTPUT
        target = int(entry_prc + score)

        # 7. DEBUG PRINT
        clean_symbol = symbol.split('26', 1)[-1] if '26' in symbol else symbol
        color = Fore.CYAN if state == "🔥" else (Fore.MAGENTA if is_counter else Fore.YELLOW)
        print(f"{color}{clean_symbol} | SIG:{active_signal} | ST:{state} | TGT:{target}")
        
        return target

    except Exception:
        return 0


