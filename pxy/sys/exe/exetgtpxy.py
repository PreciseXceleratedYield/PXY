# =============================================================================
# ENGINE COMPONENT MODULE: exetgtpxy.py
# INDIVIDUAL POSITION LEVEL TARGET PRICE ENGINE
# =============================================================================
from colorama import Fore, Style, init

# Initialize colorama for clean, colored terminal output formatting
init(autoreset=True)

# Global Switch Configuration
# Valid Options: 'SUPERTREND' or 'EXIT' (Defaults to 'SUPERTREND' on invalid input)
TARGET_MODE = 'EXIT'


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
    """Calculates individual option layer target price using isolated binary matrices.

    Execution logic uses your original row processing structure:
      - Fully Aligned / Favourable: (atr * atr) percentage target setup.
      - Anything Else (Opposite, Neutral, or Side): Strict 1.4% floor target.
      
    Capping Constraint: target_pct is strictly capped at a maximum of 49.0.
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
        mode = str(TARGET_MODE).upper().strip()

        is_ce = "CE" in symbol
        is_pe = "PE" in symbol

        if not is_ce and not is_pe:
            return round(entry_prc, 2)

        target_pct = 0.0

        # 4️⃣ Symmetrical Binary Evaluation Matrices (Aligned vs Else)
        if mode == "EXIT":
            active_exit = str(row.get("exit", "NONE")).upper().strip()
            
            if is_ce:
                target_pct = atr * atr if active_exit in ("BUY", "BULL", "NONE") else 1.4
            elif is_pe:
                target_pct = atr * atr if active_exit in ("SELL", "BEAR", "NONE") else 1.4

        else:  # Fallback Default: 'SUPERTREND' Mode
            super_trend = str(row.get("supertrend", "NONE")).upper().strip()
            
            if is_ce:
                target_pct = atr * atr if super_trend in ("BUY", "BULL", "NONE") else 1.4
            elif is_pe:
                target_pct = atr * atr if super_trend in ("SELL", "BEAR", "NONE") else 1.4

        # 5️⃣ Hard ceiling enforcement: Cap absolute target percentage at 49.0
        target_pct = min(target_pct, 49.0)

        # 6️⃣ Final mathematical target premium projection calculation
        calculated_target = entry_prc * (1.0 + (target_pct / 100.0))
        return round(calculated_target, 2)

    except Exception as e:
        print(f"{Fore.RED}Error in target_price engine: {e}{Style.RESET_ALL}")
        return 0.0


