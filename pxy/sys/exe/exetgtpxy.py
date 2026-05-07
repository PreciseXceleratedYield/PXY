import pytz
from datetime import datetime
from colorama import init, Fore, Style

init(autoreset=True)
IST = pytz.timezone("Asia/Kolkata")

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
        # 1. ENTRY DATA
        entry_prc = i(row.get("pxy_entry") or row.get("buy_prc"))
        if entry_prc <= 0:
            return 0

        # 2. BASE CALCULATION (ATR/3)
        # ATR floor of 6 ensures BASE_SCORE is always at least 2.0%
        atr_val = f(row.get("atr"), 6.0)
        BASE_SCORE = atr_val / 3
        
        # 3. SIGNAL & CONTEXT LOGIC
        symbol = str(row.get("symbol", "UNKNOWN")).upper()
        is_ce, is_pe = "CE" in symbol, "PE" in symbol
        active_signal = str(row.get("exit", "NONE")).upper()
        is_counter = str(row.get("counter", "N")).upper() == "Y"
        clean_symbol = symbol.split('26', 1)[-1] if '26' in symbol else symbol

        # 4. FIELD DEFINITIONS
        hce_d = f(row.get("hkin_ce_depth"), 1.0)
        hpe_d = f(row.get("hkin_pe_depth"), 1.0)
        ce_p = f(row.get("ce_power"), 1.0)
        pe_p = f(row.get("pe_power"), 1.0)
        ce_f = f(row.get("ce_force"), 1.0)
        pe_f = f(row.get("pe_force"), 1.0)

        # 5. FINAL PERCENTAGE SCORE CALCULATION
        state = "⏳"
        final_pct_score = BASE_SCORE # Default fallback (ATR/3)
        
        bullish_triggers = ["BUY", "BULL", "OTMBUY", "ATMBUY"]
        bearish_triggers = ["SELL", "BEAR", "OTMSELL", "ATMSELL"]

        # Calculate Fire (🔥) Percentage if aligned
        if is_ce:
            if any(t in active_signal for t in bullish_triggers):
                calc = (atr_val / hce_d * ce_f * ce_p)
                state, final_pct_score = "🔥", max(BASE_SCORE, calc)
        elif is_pe:
            if any(t in active_signal for t in bearish_triggers):
                calc = (atr_val / hpe_d * pe_f * pe_p)
                state, final_pct_score = "🔥", max(BASE_SCORE, calc)

        # 8. MAX CAP LOGIC (99%)
        # Ensure the percentage added never exceeds 99%
        if final_pct_score > 99.0:
            final_pct_score = 99.0

        # 6. FINAL OUTPUT (Score as Percentage Add)
        add_value = entry_prc * (final_pct_score / 100.0)
        target = int(entry_prc + add_value)

        # 7. DEBUG PRINT
        color = Fore.CYAN if state == "🔥" else (Fore.MAGENTA if is_counter else Fore.YELLOW)
        print(f"{color}{clean_symbol} | SIG:{active_signal} | ST:{state}")

        return target
    except Exception:
        return 0



