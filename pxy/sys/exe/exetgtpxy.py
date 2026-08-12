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
    
    Aligned Trades : 33% target premium projection.
    Hostile Trades : 1.4% base expanded dynamically via REVERSED (Opposite / Own) Count & Money factors.
                     Guaranteed to maintain a strict minimum floor of 1.4%.
    """
    try:
        # 1️⃣ Entry data execution health check
        entry_prc = f(row.get("pxy_entry") or row.get("buy_prc"))
        if entry_prc <= 0:
            return 0.0

        # 2️⃣ Context string extractors
        symbol = str(row.get("symbol", "unknown")).upper()
        active_exit = str(row.get("exit", "NONE")).upper().strip()

        is_ce = "CE" in symbol
        is_pe = "PE" in symbol

        if not is_ce and not is_pe:
            return round(entry_prc, 2)

        # 3️⃣ Extraction of structural telemetry data injected into the row
        ce_lots = i(row.get("ce_lots", 0))
        pe_lots = i(row.get("pe_lots", 0))
        ce_investment = f(row.get("ce_investment", 0.0))
        pe_investment = f(row.get("pe_investment", 0.0))

        target_pct = 0.0

        # 4️⃣ Dynamic execution logic using reversed factor framework scaling 1.4% base
        if is_ce:
            if active_exit in ("SELL", "BEAR"):  # Hostile (Not Aligned)
                # 🔄 REVERSED: Opposite (PE) / Own (CE)
                own_count, opp_count = ce_lots, pe_lots
                own_money, opp_money = ce_investment, pe_investment

                if ce_lots == 0 or pe_lots == 0 or ce_lots == pe_lots:
                    rev_count_factor = 1.0
                else:
                    rev_count_factor = float(opp_count) / float(own_count)

                if ce_investment <= 0.0 or pe_investment <= 0.0 or ce_investment == pe_investment:
                    rev_money_factor = 1.0
                else:
                    rev_money_factor = float(opp_money) / float(own_money)

                # Safe compounding cap bounds protection (Floor: 0.2, Ceiling: 5.0)
                rev_compound_factor = max(0.2, min(5.0, rev_count_factor * rev_money_factor))
                
                # FIX: Apply calculation and enforce a strict minimum baseline target floor of 1.4%
                target_pct = max(2.0, 2.0 * rev_compound_factor)
            else:                                # Aligned
                target_pct = 33.0

        elif is_pe:
            if active_exit in ("BUY", "BULL"):   # Hostile (Not Aligned)
                # 🔄 REVERSED: Opposite (CE) / Own (PE)
                own_count, opp_count = pe_lots, ce_lots
                own_money, opp_money = pe_investment, ce_investment

                if ce_lots == 0 or pe_lots == 0 or ce_lots == pe_lots:
                    rev_count_factor = 1.0
                else:
                    rev_count_factor = float(opp_count) / float(own_count)

                if ce_investment <= 0.0 or pe_investment <= 0.0 or ce_investment == pe_investment:
                    rev_money_factor = 1.0
                else:
                    rev_money_factor = float(opp_money) / float(own_money)

                # Safe compounding cap bounds protection (Floor: 0.2, Ceiling: 5.0)
                rev_compound_factor = max(0.2, min(5.0, rev_count_factor * rev_money_factor))
                
                # FIX: Apply calculation and enforce a strict minimum baseline target floor of 1.4%
                target_pct = max(2.0, 2.0 * rev_compound_factor)
            else:                                # Aligned
                target_pct = 33.0

        # 5️⃣ Final mathematical target premium projection calculation
        calculated_target = entry_prc * (1 + (target_pct / 100.0))
        return round(calculated_target, 2)

    except Exception as e:
        print(f"{Fore.RED}Error in target_price engine: {e}{Style.RESET_ALL}")
        return 0.0

