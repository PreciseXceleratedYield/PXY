# sys/exe/exetgtpxy_dashboard.py
import math
from colorama import init, Fore, Style

# Initialize Colorama
init(autoreset=True)

# ✅ GLOBAL PRINT FLAG (SET THIS TO False TO DISABLE PRINTS)
PRINT_DASHBOARD = True


def target_price(row):
    """
    3-PHASE OPTION TARGET (Premium Based):
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
        atr = float(row.get("atr", 20))
        ce_p = float(row.get("ce_power", 1.0))
        pe_p = float(row.get("pe_power", 1.0))

        exit_type = str(row.get("exit", "NONE")).upper()

        # 3️⃣ ALIGNMENT
        if "CE" in symbol:
            power = ce_p
            depth = int(row.get("hkin_ce_depth", 0))
            is_aligned = ("BUY" in exit_type) or ("BULL" in exit_type)

        elif "PE" in symbol:
            power = pe_p
            depth = int(row.get("hkin_pe_depth", 0))
            is_aligned = ("SELL" in exit_type) or ("BEAR" in exit_type)

        else:
            return entry_prc

        # 4️⃣ TARGET LOGIC
        if not is_aligned:
            total_points = 10.0
            phase = "Phase 3 (Misalignment)"

        elif depth >= 2:
            total_points = atr * power * min(depth, 5)
            phase = "Phase 2 (Deep Trend)"

        else:
            total_points = max(10.0, atr * power)
            phase = "Phase 1 (Initial Entry)"

        total_points = min(total_points, 99.0)

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
            print(f"{Fore.CYAN}ATR             : {Fore.YELLOW}{atr}")
            print(f"{Fore.CYAN}Power           : {Fore.YELLOW}{power}")
            print(f"{Fore.CYAN}Phase           : {Fore.YELLOW}{phase}")
            print(f"{Fore.CYAN}Target Pts      : {Fore.YELLOW}{total_points}")
            print(f"{Fore.CYAN}Final Target    : {Fore.GREEN}{round(target, 2)}")
            print(f"{'-'*42}\n")

        return round(target, 2)

    except Exception as e:
        if PRINT_DASHBOARD:
            print(Fore.RED + f"Error calculating target: {e}")
        fallback = round(min(float(row.get("pxy_entry", 0)) + 10, 99), 2)
        return fallback
