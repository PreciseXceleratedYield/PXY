# sys/exe/exetgtpxy_dashboard.py
import math
from colorama import init, Fore, Style

# Initialize Colorama
init(autoreset=True)

# ✅ GLOBAL PRINT FLAG (SET THIS TO False TO DISABLE PRINTS)
PRINT_DASHBOARD = False

# -------------------- CONFIG --------------------
MAX_TOTAL_POINTS = 99.0  # Cap for total points
BUFFER = 0               # Can reduce misalignment further if needed

# Configurable points per phase
PHASE_POINTS = {
    "MISALIGN": 7,   # Misalignment points
    "PHASE1": 14,    # Depth <= 2
    "PHASE2": 14     # Depth > 2, will add depth dynamically
}

# -------------------- FUNCTION --------------------
def target_price(row):
    """
    3-PHASE OPTION TARGET (Simplified Depth-Based):
    """
    try:
        # 1️⃣ BASELINE PRICE
        dynamic_entry = float(row.get("pxy_entry", 0))
        actual_price = float(row.get("buy_prc", 0))
        symbol = str(row.get("symbol", "")).upper()
        
        entry_prc = dynamic_entry if dynamic_entry > 0 else actual_price
        if entry_prc <= 0:
            return 0

        # 2️⃣ METRICS
        ce_p = float(row.get("ce_power", 1.0))
        pe_p = float(row.get("pe_power", 1.0))
        exit_type = str(row.get("exit", "NONE")).upper()

        # 3️⃣ ALIGNMENT
        if "CE" in symbol:
            depth = int(row.get("hkin_ce_depth", 0))
            is_aligned = exit_type in {"BUY", "BULL", "NONE"}
        elif "PE" in symbol:
            depth = int(row.get("hkin_pe_depth", 0))
            is_aligned = exit_type in {"SELL", "BEAR", "NONE"}
        else:
            return entry_prc

        # 4️⃣ TARGET LOGIC (simplified)
        if not is_aligned:
            total_points = PHASE_POINTS["MISALIGN"]
            phase = "Phase 3 (Misalignment)"
        elif depth <= 2:
            total_points = PHASE_POINTS["PHASE1"]
            phase = "Phase 1 (Shallow Trend)"
        else:  # depth > 2
            total_points = PHASE_POINTS["PHASE2"] + depth
            phase = "Phase 2 (Deep Trend)"

        # Cap total points
        total_points = min(total_points, MAX_TOTAL_POINTS)

        # 5️⃣ FINAL TARGET
        target = entry_prc + total_points

        # 6️⃣ CONDITIONAL PRINT
        if PRINT_DASHBOARD:
            print(f"{'-'*42}")
            print(f"{Fore.CYAN}SYMBOL          : {Fore.YELLOW}{symbol}")
            print(f"{Fore.CYAN}Actual Price    : {Fore.YELLOW}{actual_price}")
            print(f"{Fore.CYAN}Dynamic Entry   : {Fore.YELLOW}{dynamic_entry}")
            print(f"{Fore.CYAN}Used Baseline   : {Fore.YELLOW}{entry_prc}")
            print(f"{Fore.CYAN}Exit            : {Fore.YELLOW}{exit_type}")
            print(f"{Fore.CYAN}Depth           : {Fore.YELLOW}{depth}")
            print(f"{Fore.CYAN}Phase           : {Fore.YELLOW}{phase}")
            print(f"{Fore.CYAN}Target Pts      : {Fore.YELLOW}{total_points}")
            print(f"{Fore.CYAN}Final Target    : {Fore.GREEN}{round(target, 2)}")
            print(f"{'-'*42}\n")

        return round(target, 2)

    except Exception as e:
        print(f"Error calculating target for {row.get('symbol', 'UNKNOWN')}: {e}")
        return 0
