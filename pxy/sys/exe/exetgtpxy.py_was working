from colorama import Fore, Style, init

# Initialize colorama for colored console logs
init(autoreset=True)

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
        # 1. ENTRY DATA CHECK
        entry_prc = i(row.get("pxy_entry") or row.get("buy_prc"))
        if entry_prc <= 0:
            return 0

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
        
        # Supertrend field capture and sanitization
        supertrend_val = str(row.get("supertrend", "NONE")).upper().strip()

        # 4. FIELD DEFINITIONS
        hce_d = f(row.get("hkin_ce_depth"), 1.0)
        hpe_d = f(row.get("hkin_pe_depth"), 1.0)
        ce_p = f(row.get("ce_power"), 1.0)
        pe_p = f(row.get("pe_power"), 1.0)

        # Main Exit Signal Classifications
        is_bullish_signal = clean_signal in ("BUY", "BULL")
        is_bearish_signal = clean_signal in ("SELL", "BEAR")
        
        # Supertrend Directional Counter Classifications
        st_is_bearish_counter = supertrend_val in ("BEAR", "SELL", "STSELL")
        st_is_bullish_counter = supertrend_val in ("BULL", "BUY", "STBUY")

        # Core scaling math multipliers
        ce_calc = (atr_val * ce_p) + hce_d
        pe_calc = (atr_val * pe_p) + hpe_d

        # 5. FINAL PERCENTAGE SCORE CALCULATION
        state = "⏳"
        final_pct_score = BASE_SCORE

        # ==============================================================================
        # 🎯 DIRECT SIGNAL & ENGINE (RESTORED EXACT STRUCTURAL MATRIX)
        # ==============================================================================
        if is_ce:
            if is_counter and is_bullish_signal:
                # Opposite ST Block during Counter Setup
                if st_is_bearish_counter:
                    state = "🚨"
                    final_pct_score = 2 * ce_p
                else:
                    state = "🎯"  
                    final_pct_score = max(BASE_SCORE, ce_calc) 
            elif is_counter and is_bearish_signal:
                # Flat Opposite Signal Block
                state = "🚨"  
                final_pct_score = 2   
            elif is_bullish_signal:
                # No counter scenario -> Check Supertrend, then ACCELERATE
                if st_is_bearish_counter:
                    state = "🚨"
                    final_pct_score = 2 * ce_p
                else:
                    state, final_pct_score = "🔥", max(BASE_SCORE, ce_calc)
            elif is_bearish_signal:
                # Flat Opposite Signal Block
                state = "🚨"
                final_pct_score = 2
                
        elif is_pe:
            if is_counter and is_bearish_signal:
                # Opposite ST Block during Counter Setup
                if st_is_bullish_counter:
                    state = "🚨"
                    final_pct_score = 2 * pe_p
                else:
                    state = "🎯"  
                    final_pct_score = max(BASE_SCORE, pe_calc)  
            elif is_counter and is_bullish_signal:
                # Flat Opposite Signal Block
                state = "🚨"  
                final_pct_score = 2   
            elif is_bearish_signal:
                # No counter scenario -> Check Supertrend, then ACCELERATE
                if st_is_bullish_counter:
                    state = "🚨"
                    final_pct_score = 2 * pe_p
                else:
                    state, final_pct_score = "🔥", max(BASE_SCORE, pe_calc)
            elif is_bullish_signal:
                # Flat Opposite Signal Block
                state = "🚨"
                final_pct_score = 2

        # ==============================================================================
        # 🛡️ GLOBAL CRITICAL FLOORS & CEILINGS ENGINE
        # ==============================================================================
        # CRITICAL REQ: Enforce an absolute minimum floor limit of 1.4% everywhere
        if final_pct_score < 2.0:
            final_pct_score = 2.0

        # 6. MAX CAP LOGIC (Hard capped at 99%)
        if final_pct_score > 99.0:
            final_pct_score = 99.0

        # 7. FINAL TARGET CONVERSION
        add_value = entry_prc * (final_pct_score / 100.0)
        target = int(entry_prc + add_value)

        # 8. SUPPRESSED DEBUG PRINT
        if side not in PRINTED_SIDES and side != "NA":
            color = (
                Fore.CYAN if state == "🔥" else (
                    Fore.RED if state == "🚨" else (Fore.MAGENTA if state == "🎯" else Fore.YELLOW)
                )
            )
            print(f" {color}{side:<2} SCORE | {final_pct_score:>4.1f}% | ST:{state} | trend:{supertrend_val}")
            PRINTED_SIDES.add(side)

        return target

    except Exception:
        return 0

