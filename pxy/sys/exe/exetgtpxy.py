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
    """
    Calculates the target price and the final percentage score.
    Returns:
        tuple: (target_price, final_pct_score)
    """
    global PRINTED_SIDES
    try:
        # 1. ENTRY DATA CHECK
        entry_prc = i(row.get("pxy_entry") or row.get("buy_prc") or row.get("entry_prc"))
        if entry_prc <= 0:
            print(f"{Fore.RED}[DEBUG SKIP] Skipping row due to missing or invalid entry price: {entry_prc}")
            return 0, 0.0

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
                if st_is_bearish_counter:
                    state = "🚨"
                    final_pct_score = 2 * ce_p
                else:
                    state = "🎯"  
                    final_pct_score = max(BASE_SCORE, ce_calc) 
            elif is_counter and is_bearish_signal:
                state = "🚨"  
                final_pct_score = 2   
            elif is_bullish_signal:
                if st_is_bearish_counter:
                    state = "🚨"
                    final_pct_score = 2 * ce_p
                else:
                    state, final_pct_score = "🔥", max(BASE_SCORE, ce_calc)
            elif is_bearish_signal:
                state = "🚨"
                final_pct_score = 2
                
        elif is_pe:
            if is_counter and is_bearish_signal:
                if st_is_bullish_counter:
                    state = "🚨"
                    final_pct_score = 2 * pe_p
                else:
                    state = "🎯"  
                    final_pct_score = max(BASE_SCORE, pe_calc)  
            elif is_counter and is_bullish_signal:
                state = "🚨"  
                final_pct_score = 2   
            elif is_bearish_signal:
                if st_is_bullish_counter:
                    state = "🚨"
                    final_pct_score = 2 * pe_p
                else:
                    state, final_pct_score = "🔥", max(BASE_SCORE, pe_calc)
            elif is_bullish_signal:
                state = "🚨"
                final_pct_score = 2

        # Cache evaluating raw metric prior to modifying variables
        raw_pct_score = final_pct_score

        # ==============================================================================
        # 🛡️ GLOBAL CRITICAL FLOORS & CEILINGS ENGINE
        # ==============================================================================
        floor_applied = False
        if final_pct_score <= 2.0:
            final_pct_score = 3.0
            floor_applied = True

        cap_applied = False
        if final_pct_score > 99.0:
            final_pct_score = 99.0
            cap_applied = True

        # 7. FINAL TARGET CONVERSION
        add_value = entry_prc * (final_pct_score / 100.0)
        target = int(entry_prc + add_value)

        # ==============================================================================
        # 🔍 FULL VERBOSE DEBUG PRINT ENGINE (EXECUTES EVERY ROW)
        # ==============================================================================
        color = (
            Fore.CYAN if state == "🔥" else (
                Fore.RED if state == "🚨" else (Fore.MAGENTA if state == "🎯" else Fore.YELLOW)
            )
        )
        
        print(f"\n{Fore.WHITE}{'='*60}")
        print(f"{Fore.GREEN}[DEBUG MATCH] Symbol: {symbol} | Side: {side}")
        print(f"{Fore.WHITE}{'-'*60}")
        print(f"  > Inputs      | Entry: {entry_prc} | ATR: {atr_val} | Exit Sig: {clean_signal} | Counter: {is_counter} | ST: {supertrend_val}")
        print(f"  > Power/Depth | CE_Pow: {ce_p} | PE_Pow: {pe_p} | CE_Depth: {hce_d} | PE_Depth: {hpe_d}")
        print(f"  > Math Calcs  | BASE_SCORE: {BASE_SCORE:.2f} | ce_calc: {ce_calc:.2f} | pe_calc: {pe_calc:.2f}")
        print(f"  > Matrix Out  | State: {state} | Raw Score: {raw_pct_score:.2f}%")
        
        if floor_applied:
            print(f"  > Engine Mod  | {Fore.YELLOW}Floor Applied! Boosted <= 2.0% up to 3.0%")
        if cap_applied:
            print(f"  > Engine Mod  | {Fore.RED}Cap Applied! Restricted > 99.0% down to 99.0%")
            
        print(f"  > Final Execution Result:")
        print(f"    {color}{side:<2} SCORE: {final_pct_score:>4.1f}% | Added Val: +{add_value:.2f} | Final Target Prc: {target}")
        print(f"{Fore.WHITE}{'='*60}\n")

        # Standard non-verbose console print fallback matching old pattern if needed elsewhere
        PRINTED_SIDES.add(side)

        return target, final_pct_score

    except Exception as e:
        print(f"{Fore.RED}[DEBUG CRITICAL EXCEPTION]: {str(e)}")
        return 0, 0.0
