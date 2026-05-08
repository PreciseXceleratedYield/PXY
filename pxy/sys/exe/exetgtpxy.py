import pytz
from datetime import datetime
from colorama import init, Fore, Style

init(autoreset=True)
IST = pytz.timezone("Asia/Kolkata")

# Global set to track printed sides for the current refresh cycle
PRINTED_SIDES = set()

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
    global PRINTED_SIDES
    try:
        # 1. ENTRY DATA
        entry_prc = i(row.get("pxy_entry") or row.get("buy_prc"))
        if entry_prc <= 0:
            return 0

        # 2. BASE CALCULATION
        atr_val = f(row.get("atr"), 6.0)
        BASE_SCORE = atr_val * 2

        # 3. SIGNAL & CONTEXT LOGIC
        symbol = str(row.get("symbol", "UNKNOWN")).upper()
        side = "CE" if "CE" in symbol else "PE" if "PE" in symbol else "NA"
        
        is_ce, is_pe = (side == "CE"), (side == "PE")
        active_signal = str(row.get("exit", "NONE")).upper()
        is_counter = str(row.get("counter", "N")).upper() == "Y"

        # 4. FIELD DEFINITIONS
        hce_d = f(row.get("hkin_ce_depth"), 1.0)
        hpe_d = f(row.get("hkin_pe_depth"), 1.0)
        ce_p = f(row.get("ce_power"), 1.0)
        pe_p = f(row.get("pe_power"), 1.0)
        ce_f = f(row.get("ce_force"), 1.0)
        pe_f = f(row.get("pe_force"), 1.0)

        # 5. FINAL PERCENTAGE SCORE CALCULATION
        state = "⏳"
        final_pct_score = BASE_SCORE
        bullish_triggers = ["BUY", "BULL", "OTMBUY", "ATMBUY"]
        bearish_triggers = ["SELL", "BEAR", "OTMSELL", "ATMSELL"]

        if is_ce:
            if any(t in active_signal for t in bullish_triggers):
                calc = (atr_val * ce_f * ce_p) + hce_d
                state, final_pct_score = "🔥", max(BASE_SCORE, calc)
            elif any(t in active_signal for t in bearish_triggers):
                # Opposing Signal: Half the score
                final_pct_score = BASE_SCORE / 2
                state = "❄️"
        
        elif is_pe:
            if any(t in active_signal for t in bearish_triggers):
                calc = (atr_val * pe_f * pe_p) + hpe_d
                state, final_pct_score = "🔥", max(BASE_SCORE, calc)
            elif any(t in active_signal for t in bullish_triggers):
                # Opposing Signal: Half the score
                final_pct_score = BASE_SCORE / 2
                state = "❄️"

        # 8. MAX CAP LOGIC
        if final_pct_score > 99.0:
            final_pct_score = 99.0

        # 6. FINAL OUTPUT
        add_value = entry_prc * (final_pct_score / 100.0)
        target = int(entry_prc + add_value)

        # 7. SUPPRESSED DEBUG PRINT (Once per side)
        if side not in PRINTED_SIDES and side != "NA":
            color = Fore.CYAN if state == "🔥" else (Fore.BLUE if state == "❄️" else (Fore.MAGENTA if is_counter else Fore.YELLOW))
            print(f"        {color}{side:<2} SCORE | {final_pct_score:>4.1f}% | ST:{state}")
            PRINTED_SIDES.add(side)

        return target
    except Exception:
        return 0



