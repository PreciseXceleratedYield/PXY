# sys/exe/exetgtpxy_dashboard.py
import math
from colorama import init, Fore, Style

# Initialize Colorama
init(autoreset=True)

PRINT_DASHBOARD = False

# -------------------- CONFIG --------------------
MAX_TOTAL_POINTS = 99.0
BUFFER = 0

PHASE_POINTS = {
    "MISALIGN": "ATR",
    "PHASE1": "ATR + 3",
    "PHASE2": "ATR + DEPTH"
}

# -------------------- SAFE EVALUATOR --------------------
def resolve_points(expr, atr, depth):
    """
    SAFE parser (NO eval)
    Supports:
    - ATR
    - DEPTH
    - + constant math only
    """

    if isinstance(expr, (int, float)):
        return float(expr)

    if not isinstance(expr, str):
        return 0

    expr = expr.upper().replace(" ", "")

    # base values
    base = 0.0

    # case: ATR only
    if expr == "ATR":
        return atr

    # case: ATR + DEPTH
    if expr == "ATR+DEPTH":
        return atr + depth

    # case: ATR + number
    if expr.startswith("ATR+"):
        try:
            val = float(expr.replace("ATR+", ""))
            return atr + val
        except:
            return atr

    # fallback
    return atr


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

        # ATR (SAFE)
        atr = float(row.get("atr", 0))
        if atr <= 0:
            atr = entry_prc * 0.01  # fallback 1%

        # 3️⃣ ALIGNMENT
        if "CE" in symbol:
            depth = int(row.get("hkin_ce_depth", 0))
            is_aligned = exit_type in {"BUY", "BULL", "NONE"}
        elif "PE" in symbol:
            depth = int(row.get("hkin_pe_depth", 0))
            is_aligned = exit_type in {"SELL", "BEAR", "NONE"}
        else:
            return entry_prc

        # 4️⃣ TARGET LOGIC
        if not is_aligned:
            total_points = resolve_points(PHASE_POINTS["MISALIGN"], atr, depth)
            phase = "Phase 3 (Misalignment)"
        elif depth <= 2:
            total_points = resolve_points(PHASE_POINTS["PHASE1"], atr, depth)
            phase = "Phase 1 (Shallow Trend)"
        else:
            total_points = resolve_points(PHASE_POINTS["PHASE2"], atr, depth)
            phase = "Phase 2 (Deep Trend)"

        # optional depth add (your original behavior preserved)
        if depth > 2:
            total_points += depth

        # Cap
        total_points = min(total_points, MAX_TOTAL_POINTS)

        # 5️⃣ FINAL TARGET
        target = entry_prc + total_points

        # 6️⃣ DEBUG
        if PRINT_DASHBOARD:
            print(f"{'-'*42}")
            print(f"{Fore.CYAN}SYMBOL          : {Fore.YELLOW}{symbol}")
            print(f"{Fore.CYAN}ENTRY           : {Fore.YELLOW}{entry_prc}")
            print(f"{Fore.CYAN}ATR             : {Fore.YELLOW}{atr}")
            print(f"{Fore.CYAN}DEPTH           : {Fore.YELLOW}{depth}")
            print(f"{Fore.CYAN}PHASE           : {Fore.YELLOW}{phase}")
            print(f"{Fore.CYAN}TARGET POINTS   : {Fore.YELLOW}{total_points}")
            print(f"{Fore.CYAN}FINAL TARGET    : {Fore.GREEN}{round(target, 2)}")
            print(f"{'-'*42}\n")

        return round(target, 2)

    except Exception as e:
        print(f"Error calculating target for {row.get('symbol', 'UNKNOWN')}: {e}")
        return 0
