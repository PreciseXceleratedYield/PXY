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
    """Calculates individual option layer target price using dynamic volatility variables.

    Aligned Trades   : atr + vol_component (Minimum floor of 25.0, 4:1 dampened growth thereafter).
    Sideways Trades  : Strict ATR alone split by 1.4 (Quick escape targeting to beat sideways Theta decay).
    Hostile Trades   : Fixed 1.4% target percentage floor.
    """
    try:
        # 1️⃣ Entry data execution health check
        entry_prc = f(row.get("pxy_entry") or row.get("buy_prc"))
        if entry_prc <= 0:
            return 0.0

        # 2️⃣ INPUTS (SAFE) & PRE-CALCULATIONS
        atr = f(row.get("atr", 0))
        
        # Calculate volatility component once for the Aligned Strategy
        raw_vol = (atr * atr) + (atr + atr)
        
        # 🎯 FIX APPLIED: Changed 'raw_val' to 'raw_vol' to match the variable above
        vol_component = max(24, min(raw_vol, 76))
        
        # 3️⃣ Context string extractors
        symbol = str(row.get("symbol", "unknown")).upper()
        active_exit = str(row.get("exit", "NONE")).upper().strip()
        supertrend = str(row.get("supertrend", "NONE")).upper().strip()
        boss = str(row.get("bos_val", "NONE")).upper().strip()

        is_ce = "CE" in symbol
        is_pe = "PE" in symbol

        if not is_ce and not is_pe:
            return round(entry_prc, 2)

        target_pct = 0.0

        # 4️⃣ 3-Tier Target Profit Matrix Engine
        if is_ce:
            if active_exit in ("SELL", "BEAR"):
                target_pct = 1.4
            else:
                target_pct = (atr + vol_component) if boss == "NBUY" else vol_component

        elif is_pe:
            if active_exit in ("BUY", "BULL"):
                target_pct = 1.4
            else:
                target_pct = (atr + vol_component) if boss == "NSELL" else vol_component

        # 5️⃣ Final mathematical target premium projection calculation
        calculated_target = entry_prc * (1.0 + (target_pct / 100.0))
        return round(calculated_target, 2)

    except Exception as e:
        print(f"{Fore.RED}Error in target_price engine: {e}{Style.RESET_ALL}")
        return 0.0
