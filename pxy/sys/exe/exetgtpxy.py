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

        # ==============================================================================
        # 🚨 HARD TRIGGER EXITS (CORRIDOR OVERRIDES)
        # ==============================================================================
        # Rule 1: Kill all PE trades immediately if trend does NOT contain BEAR, SELL, or STSELL
        if is_pe and not any(term in supertrend_val for term in ["BEAR", "SELL", "STSELL"]):
            if side not in PRINTED_SIDES:
                print(f" {Fore.RED}💥 PE FORCE KILL {side:<2} | TREND IS NOT BEARISH ({supertrend_val}) -> EMERGENCY EXIT")
                PRINTED_SIDES.add(side)
            return 1  # Bypasses all math. Forces immediate exit execution loop downstream.

        # Rule 2: Flip for CE trades. Kill if trend does NOT contain BULL, BUY, or STBUY
        if is_ce and not any(term in supertrend_val for term in ["BULL", "BUY", "STBUY"]):
            if side not in PRINTED_SIDES:
                print(f" {Fore.RED}💥 CE FORCE KILL {side:<2} | TREND IS NOT BULLISH ({supertrend_val}) -> EMERGENCY EXIT")
                PRINTED_SIDES.add(side)
            return 1  # Bypasses all math. Forces immediate exit execution loop downstream.

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

        # Core scaling math multipliers (Enforced universally now)
        ce_calc = atr_val * ce_p
        pe_calc = atr_val * pe_p

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
                    final_pct_score = 1.4 * ce_p
                else:
                    state = "🎯"  
                    # ACCELERATED: Uses full scaling math multiplier instead of max cap rules
                    final_pct_score = ce_calc
            elif is_counter and is_bearish_signal:
                # Flat Opposite Signal Block
                state = "🚨"  
                final_pct_score = 1.4   
            elif is_bullish_signal:
                # No counter scenario -> Check Supertrend, then ACCELERATE
                if st_is_bearish_counter:
                    state = "🚨"
                    final_pct_score = 1.4 * ce_p
                else:
                    state, final_pct_score = "🔥", ce_calc
            elif is_bearish_signal:
                # Flat Opposite Signal Block
                state = "🚨"
                final_pct_score = 1.4
                
        elif is_pe:
            if is_counter and is_bearish_signal:
                # Opposite ST Block during Counter Setup
                if st_is_bullish_counter:
                    state = "🚨"
                    final_pct_score = 1.4 * pe_p
                else:
                    state = "🎯"  
                    # ACCELERATED: Uses full scaling math multiplier instead of max cap rules
                    final_pct_score = pe_calc  
            elif is_counter and is_bullish_signal:
                # Flat Opposite Signal Block
                state = "🚨"  
                final_pct_score = 1.4   
            elif is_bearish_signal:
                # No counter scenario -> Check Supertrend, then ACCELERATE
                if st_is_bullish_counter:
                    state = "🚨"
                    final_pct_score = 1.4 * pe_p
                else:
                    state, final_pct_score = "🔥", pe_calc
            elif is_bullish_signal:
                # Flat Opposite Signal Block
                state = "🚨"
                final_pct_score = 1.4

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


