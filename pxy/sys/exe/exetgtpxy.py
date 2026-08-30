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
    
    Aligned Trades : atr * atr (Normal growth up to 25, 4:1 dampened growth thereafter).
    Hostile Trades : Fixed 1.4% target percentage floor.
    """
    try:
        # 1️⃣ Entry data execution health check
        entry_prc = f(row.get("pxy_entry") or row.get("buy_prc"))
        if entry_prc <= 0:
            return 0.0

        # 2️⃣ INPUTS (SAFE)
        ce_p = f(row.get("ce_power", 1))
        pe_p = f(row.get("pe_power", 1))

        ce_d = i(row.get("hkin_ce_depth", 0))
        pe_d = i(row.get("hkin_pe_depth", 0))
        
        atr = f(row.get("atr", 0))
        katr = max(f(row.get("katr", 1)), 0.001)  # prevent divide-by-zero

        # Extract raw bos_val to check if it's text "NONE" or blank
        raw_bos = str(row.get("bos_val", "NONE")).upper().strip()
        is_bos_none = (raw_bos == "NONE" or raw_bos == "")

        # 3️⃣ Context string extractors
        symbol = str(row.get("symbol", "unknown")).upper()
        active_exit = str(row.get("exit", "NONE")).upper().strip()

        is_ce = "CE" in symbol
        is_pe = "PE" in symbol

        if not is_ce and not is_pe:
            return round(entry_prc, 2)

        target_pct = 0.0

        # 4️⃣ Dynamic execution logic using flattened ATR^2 capping formula
        if is_ce:
            if active_exit in ("SELL", "BEAR"):  # Hostile (Not Aligned)
                target_pct = 1.4
            else:                                # Aligned
                target_pct = min(atr**2, 25.0) + max(0.0, (atr**2 - 25.0) / 4.0)
                
        elif is_pe:
            if active_exit in ("BUY", "BULL"):   # Hostile (Not Aligned)
                target_pct = 1.4
            else:                                # Aligned
                target_pct = min(atr**2, 25.0) + max(0.0, (atr**2 - 25.0) / 4.0)

        # 5️⃣ Final mathematical target premium projection calculation
        calculated_target = entry_prc * (1.0 + (target_pct / 100.0))
        return round(calculated_target, 2)

    except Exception as e:
        print(f"{Fore.RED}Error in target_price engine: {e}{Style.RESET_ALL}")
        return 0.0
