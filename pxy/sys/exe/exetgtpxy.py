# =============================================================================
# ENGINE COMPONENT MODULE: exetgtpxy.py
# INDIVIDUAL POSITION LEVEL TARGET PRICE ENGINE
# =============================================================================
from colorama import Fore, Style, init

# Initialize colorama for clean, colored terminal output formatting
init(autoreset=True)


def f(x, d=0.0):
    """Safely cast input to float, return default if casting fails or value <=
    0.
    """
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


def target_price(row):
    """Calculates individual option layer target price using exit conditions.

    Favorite Trade Status: (atr * atr) percentage target setup. Hostile Trade Status: Strict
    1.4% percentage floor buffer.
    """
    try:
        # 1️⃣ Entry data execution health check
        entry_prc = f(row.get("pxy_entry") or row.get("buy_prc"))
        if entry_prc <= 0:
            return 0.0

        # 2️⃣ INPUTS (SAFE) & PRE-CALCULATIONS
        atr = f(row.get("atr", 0))

        # 3️⃣ Context string extractors
        symbol = str(row.get("symbol", "unknown")).upper()
        super_trend = str(row.get("supertrend", "NONE")).upper().strip()
        active_exit = str(row.get("exit", "NONE")).upper().strip()

        is_ce = "CE" in symbol
        is_pe = "PE" in symbol

        if not is_ce and not is_pe:
            return round(entry_prc, 2)

        target_pct = 0.0

        # 4️⃣ Exit-Value Only Target Matrix Logic
        if is_ce:
            # Hostile conditions for Calls
            if (super_trend in ("SELL", "BEAR")) or (active_exit in ("SELL", "BEAR")):
                target_pct = 1.4
            else:
                target_pct = atr * atr

        elif is_pe:
            # Hostile conditions for Puts
            if (super_trend in ("BUY", "BULL")) or (active_exit in ("BUY", "BULL")):
                target_pct = 1.4
            else:
                target_pct = atr * atr

        # 5️⃣ Final mathematical target premium projection calculation
        calculated_target = entry_prc * (1.0 + (target_pct / 100.0))
        return round(calculated_target, 2)

    except Exception as e:
        print(f"{Fore.RED}Error in target_price engine: {e}{Style.RESET_ALL}")
        return 0.0


