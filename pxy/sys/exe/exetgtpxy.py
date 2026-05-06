# tgtpxy.py
import pytz
from datetime import datetime
from colorama import init, Fore, Style

init(autoreset=True)
IST = pytz.timezone("Asia/Kolkata")

# ==========================================
# ⚙️ GLOBAL PARAMETER
# ==========================================
BASE = 3  # Single parameter for Multiplier, Floor %, and Default Value

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
        # 1. FIELD DEFINITIONS (Using BASE as the default)
        hce_d = f(row.get("hkin_ce_depth"), BASE)
        hpe_d = f(row.get("hkin_pe_depth"), BASE)
        ce_p = f(row.get("ce_power"), BASE)
        pe_p = f(row.get("pe_power"), BASE)
        ce_f = f(row.get("ce_force"), BASE)
        pe_f = f(row.get("pe_force"), BASE)

        # 2. ENTRY DATA
        entry_prc = i(row.get("pxy_entry") or row.get("buy_prc"))
        if entry_prc <= 0:
            return 0
            
        symbol = str(row.get("symbol", "UNKNOWN")).upper()
        is_ce, is_pe = "CE" in symbol, "PE" in symbol

        # 3. SIGNAL & COUNTER LOGIC
        exit_sig = str(row.get("exit", "NONE")).upper()
        entry_sig = str(row.get("entry", "NONE")).upper()
        is_counter = str(row.get("counter", "N")).upper() == "Y"
        
        active_signal = entry_sig if is_counter else exit_sig

        # 4. CALCULATION LOGIC (Driven by BASE)
        floor_points = int(entry_prc * (BASE / 100))
        state = "⏳"
        score = floor_points

        # Define keyword maps for SELL and BUY variations
        sell_triggers = ["SELL", "OTMSELL", "ATMSELL"]
        buy_triggers  = ["BUY", "OTMBUY", "ATMBUY"]

        if is_ce:
            # Logic: If CE and any SELL variation is found in active_signal
            if any(trigger in active_signal for trigger in sell_triggers):
                calc_score = BASE * hce_d * ce_f * ce_p
                state, score = "🔥", max(floor_points, int(calc_score))
                
        elif is_pe:
            # Logic: If PE and any BUY variation is found in active_signal
            if any(trigger in active_signal for trigger in buy_triggers):
                calc_score = BASE * hpe_d * pe_f * pe_p
                state, score = "🔥", max(floor_points, int(calc_score))

        # 5. FINAL OUTPUT
        target = int(entry_prc + score)

        # 6. DEBUG PRINT
        clean_symbol = symbol.split('26', 1)[-1] if '26' in symbol else symbol
        color = Fore.CYAN if state == "🔥" else (Fore.MAGENTA if is_counter else Fore.YELLOW)
        
        print(f"{color}{clean_symbol} | SIG:{active_signal} | ST:{state} | TGT:{target}")
        
        return target

    except Exception as e:
        # Optional: print(f"Error: {e}")
        return 0


