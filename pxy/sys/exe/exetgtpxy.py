from datetime import datetime, timedelta
from colorama import Fore, Style, init
import pytz

# Initialize colorama for colored console logs
init(autoreset=True)
IST = pytz.timezone("Asia/Kolkata")

# Global set to track printed sides for the current refresh cycle
PRINTED_SIDES = set()

def f(x, d=0.0):
    try:
        val = float(x)
        return val if val > 0 else d
    except Exception:
        return d

def i(x, d=0):
    try:
        return int(float(x))
    except Exception:
        return d

def target_price(row):
    global PRINTED_SIDES
    try:
        # 1. ENTRY DATA & FRESHNESS CHECK
        entry_prc = i(row.get("pxy_entry") or row.get("buy_prc"))
        if entry_prc <= 0:
            return 0

        # Check if trade is fresh (within 2 minutes)
        is_fresh = False
        entry_time_raw = row.get("entry_time") # Expects string "YYYY-MM-DD HH:MM:SS" or datetime object
        
        if entry_time_raw:
            if isinstance(entry_time_raw, str):
                entry_time = datetime.strptime(entry_time_raw, "%Y-%m-%d %H:%M:%S")
                entry_time = IST.localize(entry_time)
            else:
                # FIX: Ensure existing datetime objects are accurately localized or converted to IST
                if entry_time_raw.tzinfo is None:
                    entry_time = IST.localize(entry_time_raw)
                else:
                    entry_time = entry_time_raw.astimezone(IST)
                
            current_time = datetime.now(IST)
            time_diff = (current_time - entry_time).total_seconds() / 60.0
            
            if time_diff <= 2.0:
                is_fresh = True

        # 2. BASE CALCULATION
        atr_val = f(row.get("atr"), 6.0)
        BASE_SCORE = atr_val / 2

        # 3. SIGNAL & CONTEXT LOGIC
        symbol = str(row.get("symbol", "UNKNOWN")).upper()
        side = "CE" if "CE" in symbol else "PE" if "PE" in symbol else "NA"
        is_ce, is_pe = (side == "CE"), (side == "PE")
        active_signal = str(row.get("exit", "NONE")).upper()
        clean_signal = active_signal.strip()
        is_counter = str(row.get("counter", "N")).upper() == "Y"

        # 4. FIELD DEFINITIONS (Removed duplicate extractions)
        hce_d = f(row.get("hkin_ce_depth"), 1.0)
        hpe_d = f(row.get("hkin_pe_depth"), 1.0)
        ce_p = f(row.get("ce_power"), 1.0)
        pe_p = f(row.get("pe_power"), 1.0)
        ce_f = f(row.get("ce_force"), 1.0)  
        pe_f = f(row.get("pe_force"), 1.0)  

        # 5. FINAL PERCENTAGE SCORE CALCULATION (✅ FIXED: Counter-Trend takes priority over Freshness)
        state = "⏳"
        
        if is_counter:
            final_pct_score = 44.0
        elif is_fresh:
            state = "🆕"
            final_pct_score = 3.0
        else:
            final_pct_score = BASE_SCORE

            # Fast membership lookups
            is_bullish_signal = clean_signal in ("BUY", "BULL","AVGB")
            is_bearish_signal = clean_signal in ("SELL", "BEAR", "AVGS")

            # Applied your updated scaling math multipliers
            ce_calc = (1.4 * hce_d) ** min(ce_p, 2)
            pe_calc = (1.4 * hpe_d) ** min(pe_p, 2)
            if is_ce:
                if is_bullish_signal:
                    state, final_pct_score = "🔥", max(BASE_SCORE, ce_calc)
                elif is_bearish_signal:
                    state = "🚨"
                    final_pct_score = 1.4 
                    
            elif is_pe:
                if is_bearish_signal:
                    state, final_pct_score = "🔥", max(BASE_SCORE, pe_calc)
                elif is_bullish_signal:
                    state = "🚨"
                    final_pct_score = 1.4 

        # 6. MAX CAP LOGIC (Hard capped at 25%)
        if final_pct_score > 99.0:
            final_pct_score = 99.0

        # 7. FINAL TARGET CONVERSION
        add_value = entry_prc * (final_pct_score / 100.0)
        target = int(entry_prc + add_value)

        # 8. SUPPRESSED DEBUG PRINT (Once per side per refresh cycle)
        if side not in PRINTED_SIDES and side != "NA":
            color = (
                Fore.GREEN if state == "🆕" else (
                    Fore.CYAN if state == "🔥" else (
                        Fore.RED if state == "🚨" else (Fore.MAGENTA if is_counter else Fore.YELLOW)
                    )
                )
            )
            print(f" {color}{side:<2} SCORE | {final_pct_score:>4.1f}% | ST:{state}")
            PRINTED_SIDES.add(side)

        return target

    except Exception:
        return 0

