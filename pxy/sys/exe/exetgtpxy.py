# systrgtpxy.py
from datetime import datetime
from colorama import Fore, Style, init
import pytz

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
    """
    PXY Automated Target Price Matrix Engine.
    No Counter -> Target = ATR * Power
    Counter Present -> Holds position at 99% Cap until proper flip.
    Both paths evaluate exit_yield on opposite signal; exits if >= 1.4%, otherwise holds flat.
    """
    global PRINTED_SIDES
    try:
        # 1. ENTRY DATA HEALTH CHECK
        entry_prc = i(row.get("pxy_entry") or row.get("buy_prc"))
        if entry_prc <= 0:
            return 0

        # 2. EXTRACT SPREAD VOLATILITY LAYER DATA
        atr_val = f(row.get("atr"), 6.0)

        # 3. CONTEXT EXTRACTORS & SYNCHRONIZATION SIGNATURES
        symbol = str(row.get("symbol", "UNKNOWN")).upper()
        side = "CE" if "CE" in symbol else "PE" if "PE" in symbol else "NA"
        is_ce, is_pe = (side == "CE"), (side == "PE")
        
        # Ingest parameter context flags directly from your row dictionary keys
        is_counter = str(row.get("counter", "N")).upper().strip() == "Y"
        opp_signal = str(row.get("opp_signal_fired", "N")).upper().strip() == "Y"

        # 4. CAPTURE STRUCTURAL MULTIPLIER FIELDS
        hce_d = f(row.get("hkin_ce_depth"), 1.0)
        hpe_d = f(row.get("hkin_pe_depth"), 1.0)
        ce_p  = f(row.get("ce_power"), 1.0)
        pe_p  = f(row.get("pe_power"), 1.0)

        # Pre-compute local market yield definitions: (ATR * Power) + Depth
        ce_yield = (atr_val * ce_p) + hce_d
        pe_yield = (atr_val * pe_p) + hpe_d

        # 5. INITIALIZE STATE TARGET ROUTER VARIABLES
        state = "⏳"
        final_pct_score = 0.0
        trigger_opposite_exit = False

        # ==============================================================================
        # 🎯 RECONSTRUCTED LOGIC ENGINE
        # ==============================================================================
        if is_ce:
            if not is_counter:
                # 🟢 NO COUNTER CASE: Standard Target is strictly ATR * Power
                if opp_signal:
                    # Check for early opposite signal exit condition
                    if ce_yield >= 1.4:
                        trigger_opposite_exit = True
                        final_pct_score = ce_yield
                    else:
                        final_pct_score = atr_val * ce_p
                else:
                    state = "🔥"
                    final_pct_score = atr_val * ce_p
            else:
                # 🔵 COUNTER SETUP CASE: Hard lock to 99.0% to bypass targets until proper flip happens
                if opp_signal:
                    if ce_yield >= 1.4:
                        trigger_opposite_exit = True
                        final_pct_score = ce_yield
                    else:
                        # Yield failed to hit 1.4% on opposite flip -> Return original cost entry price to exit flat
                        return entry_prc 
                else:
                    state = "💎"
                    final_pct_score = 99.0  # Force hold pattern placeholder
                
        elif is_pe:
            if not is_counter:
                # 🟢 NO COUNTER CASE: Standard Target is strictly ATR * Power
                if opp_signal:
                    # Check for early opposite signal exit condition
                    if pe_yield >= 1.4:
                        trigger_opposite_exit = True
                        final_pct_score = pe_yield
                    else:
                        final_pct_score = atr_val * pe_p
                else:
                    state = "🔥"
                    final_pct_score = atr_val * pe_p
            else:
                # 🔵 COUNTER SETUP CASE: Hard lock to 99.0% to bypass targets until proper flip happens
                if opp_signal:
                    if pe_yield >= 1.4:
                        trigger_opposite_exit = True
                        final_pct_score = pe_yield
                    else:
                        # Yield failed to hit 1.4% on opposite flip -> Return original cost entry price to exit flat
                        return entry_prc 
                else:
                    state = "💎"
                    final_pct_score = 99.0  # Force hold pattern placeholder

        # ==============================================================================
        # 🛡️ GLOBAL CEILINGS & OUTPUT QUANTIFICATION
        # ==============================================================================
        if final_pct_score > 99.0:
            final_pct_score = 99.0

        # Convert score into an exact liquid point target value
        add_value = entry_prc * (final_pct_score / 100.0)
        target = int(entry_prc + add_value)

        # Console Diagnostic Report Summary Renders
        if side not in PRINTED_SIDES and side != "NA":
            if trigger_opposite_exit:
                print(f" {Fore.GREEN}{side:<2} FLIP EXIT   | Yield: {final_pct_score:>4.1f}% | Exiting on True Opposite Signal!")
            elif is_counter:
                print(f" {Fore.MAGENTA}{side:<2} HOLD TOK    | Locked at 99.0% Cap. Holding position open until opposite signal flip...")
            else:
                print(f" {Fore.CYAN}{side:<2} TREND TRACE | Standard Target Set at {final_pct_score:>4.1f}% (ATR * Power)")
            PRINTED_SIDES.add(side)

        return target

    except Exception as e:
        print(f"Target Module Exception encountered: {e}")
        return 0
