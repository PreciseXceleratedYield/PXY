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


def target_price(row):
    """Calculates individual option layer target price using exit status alignment.

    Execution logic:
      - Opposite / Counter-Trend (EXITCE for CE, EXITPE for PE exclusively): Strict 1.4% floor target.
      - Aligned / Favourable / Any other state: Strict 99.0% target setup.
    """
    try:
        # 1️⃣ Entry data execution health check
        entry_prc = f(row.get("pxy_entry") or row.get("buy_prc"))
        if entry_prc <= 0:
            return 0.0

        # 2️⃣ Context string extractors
        symbol = str(row.get("symbol", "unknown")).upper()
        derived_entry = str(row.get("entry", "")).upper().strip()

        is_ce = "CE" in symbol
        is_pe = "PE" in symbol

        if not is_ce and not is_pe:
            return round(entry_prc, 2)

        target_pct = 0.0

        # 3️⃣ Symmetrical Binary Evaluation Matrices (Strictly Exclusive Mappings)
        if is_ce:
            target_pct = 99 if derived_entry == "EXITCE" else 99
            
        elif is_pe:
            target_pct = 99 if derived_entry == "EXITPE" else 99

        # 4️⃣ Final mathematical target premium projection calculation
        calculated_target = entry_prc * (1.0 + (target_pct / 100.0))
        return round(calculated_target, 2)

    except Exception as e:
        print(f"{Fore.RED}Error in target_price engine: {e}{Style.RESET_ALL}")
        return 0.0

