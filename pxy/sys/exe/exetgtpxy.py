# sys/exe/exetgtpxy.py
from colorama import Fore, Style, init

# Initialize colorama for clean, colored terminal output formatting
init(autoreset=True)


def f(x, d=0.0):
    """Safely cast input to float, return default if casting fails or value <= 0."""
    try:
        val = float(x)
        return val if val > 0 else d
    except (ValueError, TypeError):
        return d


def i(x, d=0):
    """Safely cast input to integer, return default if casting fails."""
    try:
        return int(x)
    except (ValueError, TypeError):
        return d


def dynamic_entry(row):
    """Returns the raw entry price from row dictionary entries with no tracking variables."""
    try:
        return round(float(row.get("buy_prc", 0)), 2)
    except (ValueError, TypeError):
        return 0.0


def target_price(row):
    """Calculates individual option layer target price using advanced cross-indicator alignment matrices.
    
    1. SuperTrend Opposite              -> 1.4% Target
    2. Entry Opposite                   -> atr / 2 Target
    3. Fully Aligned (ST + Entry)       -> 99% Target
    """
    try:
        # 1️⃣ Entry data execution health check
        entry_prc = f(row.get("pxy_entry") or row.get("buy_prc"))
        if entry_prc <= 0:
            return 0.0

        # 2️⃣ INPUTS (SAFE)
        atr = f(row.get("atr", 0))

        # 3️⃣ Context and Alignment Extraction
        symbol = str(row.get("symbol", "unknown")).upper()
        st_trend = str(row.get("ST_Trend", "NONE")).upper().strip()       # SuperTrend State
        entry_sig = str(row.get("entry_signal", "NONE")).upper().strip()  # Generated Entry Type ("OTMBUY", "OTMSELL", "BULL", "BEAR")

        is_ce = "CE" in symbol
        is_pe = "PE" in symbol

        if not is_ce and not is_pe:
            return round(entry_prc, 2)

        target_pct = 0.0

        # 4️⃣ Advanced Tri-Layer Matrix Evaluation Loop
        if is_ce:
            # Check 1: SuperTrend Profile Check (Opposite State)
            if st_trend in ("BEAR", "SELL"):
                target_pct = 1.4
            # Check 2: Entry Signal Profile Check (Opposite State / Counter-Trend Play)
            elif entry_sig in ("OTMSELL", "BEAR"):
                target_pct = atr / 2.0 if atr > 0 else 1.4  # Fallback to floor if atr is empty
            # Check 3: Full structural pipeline alignment
            else:
                target_pct = 99.0

        elif is_pe:
            # Check 1: SuperTrend Profile Check (Opposite State)
            if st_trend in ("BULL", "BUY"):
                target_pct = 1.4
            # Check 2: Entry Signal Profile Check (Opposite State / Counter-Trend Play)
            elif entry_sig in ("OTMBUY", "BULL"):
                target_pct = atr / 2.0 if atr > 0 else 1.4  # Fallback to floor if atr is empty
            # Check 3: Full structural pipeline alignment
            else:
                target_pct = 99.0

        # 5️⃣ Final mathematical target premium projection calculation
        calculated_target = entry_prc * (1 + (target_pct / 100.0))
        return round(calculated_target, 2)

    except Exception as e:
        print(f"{Fore.RED}Error in target_price engine: {e}{Style.RESET_ALL}")
        return 0.0



