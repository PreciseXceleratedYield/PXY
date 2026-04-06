# sys/exe/exetgtpxy_dashboard.py
import math
from colorama import init, Fore, Style

# Initialize Colorama for colored output
init(autoreset=True)

def target_price(row):
    """
    3-PHASE OPTION TARGET (Premium Based):
    
    PHASE 1: Initial Entry (Depth < 2) -> max(10, ATR * Power)
    PHASE 2: Deep Trend (Depth >= 2 + Aligned) -> ATR * Power * Depth
    PHASE 3: Reversal / Misalignment -> Fixed 10 Points
    Cap total points at 99.
    Baseline: pxy_entry (dynamic decaying price from OMS)
    """
    try:
        # 1️⃣ BASELINE PRICE
        dynamic_entry = float(row.get("pxy_entry", 0))  # dynamic from OMS
        actual_price = float(row.get("buy_prc", 0))     # actual market price
        symbol = str(row.get("symbol", "")).upper()
        
        # fallback if dynamic_entry missing
        entry_prc = dynamic_entry if dynamic_entry > 0 else actual_price
        if entry_prc <= 0: 
            return 0

        # 2️⃣ MARKET / OMS METRICS
        atr = float(row.get("atr", 20))
        ce_p = float(row.get("ce_power", 1.0))
        pe_p = float(row.get("pe_power", 1.0))
        mullu = str(row.get("direction", "SIDE")).upper()  # UP / DOWN

        # ✅ USE EXIT INSTEAD OF ENTRY
        exit_type = str(row.get("exit", "NONE")).upper()

        # 3️⃣ PHASE & ALIGNMENT LOGIC (EXCLUSIVE)
        if "CE" in symbol:
            power = ce_p
            depth = int(row.get("hkin_ce_depth", 0))

            is_aligned = (
                (mullu == "UP") and 
                (("BUY" in exit_type) or ("BULL" in exit_type))
            )

        elif "PE" in symbol:
            power = pe_p
            depth = int(row.get("hkin_pe_depth", 0))

            is_aligned = (
                (mullu == "DOWN") and 
                (("SELL" in exit_type) or ("BEAR" in exit_type))
            )

        else:
            # Non-CE/PE: fallback to baseline price
            return entry_prc

        # 4️⃣ TARGET POINTS CALCULATION
        if not is_aligned:
            total_points = 10.0
            phase = "Phase 3 (Misalignment)"

        elif depth >= 2:
            total_points = atr * power * min(depth, 5)
            phase = "Phase 2 (Deep Trend)"

        elif depth < 2:
            total_points = max(10.0, atr * power)
            phase = "Phase 1 (Initial Entry)"

        else:
            total_points = 10.0
            phase = "Phase 3 (Fallback)"

        # 5️⃣ CAP TOTAL POINTS
        total_points = min(total_points, 99.0)

        # 6️⃣ FINAL TARGET
        target = entry_prc + total_points

        # 7️⃣ DASHBOARD PRINT
        print(f"{'-'*60}")
        print(f"{Fore.CYAN}SYMBOL          : {Fore.YELLOW}{symbol}")
        print(f"{Fore.CYAN}Actual Price    : {Fore.YELLOW}{actual_price}")
        print(f"{Fore.CYAN}Dynamic Entry   : {Fore.YELLOW}{dynamic_entry}")
        print(f"{Fore.CYAN}Used Baseline   : {Fore.YELLOW}{entry_prc}")
        print(f"{Fore.CYAN}Direction       : {Fore.YELLOW}{mullu}")
        print(f"{Fore.CYAN}Exit            : {Fore.YELLOW}{exit_type}")
        print(f"{Fore.CYAN}Depth           : {Fore.YELLOW}{depth}")
        print(f"{Fore.CYAN}ATR             : {Fore.YELLOW}{atr}")
        print(f"{Fore.CYAN}Power           : {Fore.YELLOW}{power}")
        print(f"{Fore.CYAN}Phase           : {Fore.YELLOW}{phase}")
        print(f"{Fore.CYAN}Target Pts      : {Fore.YELLOW}{total_points}")
        print(f"{Fore.CYAN}Final Target    : {Fore.GREEN}{round(target, 2)}")
        print(f"{'-'*60}\n")

        return round(target, 2)

    except Exception as e:
        print(Fore.RED + f"Error calculating target: {e}")
        fallback = round(min(float(row.get("pxy_entry", 0)) + 10, 99), 2)
        return fallback

