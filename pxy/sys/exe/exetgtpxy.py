from colorama import Fore, init

# Initialize colorama for clean, automatically reset terminal tracking outputs
init(autoreset=True)

# Global tracker set to avoid terminal printing redundancy per tick refresh cycle
PRINTED_SIDES = set()

def sanitize_float(value, fallback=0.0):
    try:
        val = float(value)
        return val if val > 0 else fallback
    except Exception:
        return fallback

def target_price(row):
    global PRINTED_SIDES
    try:
        # 1. CLEAN VALUE EXTRACTION & VERIFICATION
        entry_prc = sanitize_float(row.get("pxy_entry") or row.get("buy_prc"))
        if entry_prc <= 0:
            return 0

        # 🎯 UPDATED FALLBACK: If row.get("atr") breaks or is missing, it drops back to 7.0
        atr_val = sanitize_float(row.get("atr"), 7.0)
        symbol = str(row.get("symbol", "UNKNOWN")).upper()
        side = "CE" if "CE" in symbol else "PE" if "PE" in symbol else "NA"

        # 2. RAW SIMPLIFIED DEPTH SOURCING 
        depth_val = 1.0
        if side == "CE":
            depth_val = sanitize_float(row.get("hkin_ce_depth"), 1.0)
        elif side == "PE":
            depth_val = sanitize_float(row.get("hkin_pe_depth"), 1.0)

        # 3. DYNAMIC PERCENTAGE SCORE MATH
        # Extract counter flag directly from row data
        is_counter = str(row.get("counter", "N")).upper() == "Y"

        if is_counter:
            # If counter is active, only add
            final_pct_score = max(2.0, atr_val + depth_val)
        else:
            # Normal depth rule: subtract for depth 1-3, add for depth 4+
            final_pct_score = max(2.0, atr_val - depth_val if depth_val <= 4 else atr_val + depth_val)

        # 4. FINAL PERCENTAGE TARGET MATH CONVERSION
        add_value = entry_prc * (final_pct_score / 100.0)
        target = round(entry_prc + add_value, 2)

        # 5. STREAMLINED ACTION OUTPUT CONSOLE LOGGER
        # FIX: Track by side only instead of combining with symbol
        if side not in PRINTED_SIDES and side != "NA":
            print(f" {Fore.CYAN}{side:<2} SCORE | Target: {final_pct_score:>4.1f}%")
            PRINTED_SIDES.add(side)

        return target

    except Exception:
        return 0

