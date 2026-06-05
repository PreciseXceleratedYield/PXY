from datetime import datetime
from colorama import Fore, Style, init
import pytz

# Initialize colorama for colored terminal output
init(autoreset=True)
ist = pytz.timezone("Asia/Kolkata")

# Global set to track printed sides for the current refresh cycle
printed_sides = set()


def f(x, d=0.0):
    """Safely cast input to float, return default if casting fails or value <= 0."""
    try:
        val = float(x)
        return val if val > 0 else d
    except Exception:
        return d


def i(x, d=0):
    """Safely cast input to integer, return default if casting fails."""
    try:
        return int(float(x))
    except Exception:
        return d


def target_price(row):
    """Calculated target price based strictly on ATR and signal direction."""
    global printed_sides

    try:
        # 1. Extract base values and powers needed for printing and logic
        atr_val = f(row.get("atr"), 6.0)
        ce_power = f(row.get("ce_power"), 1.0)
        pe_power = f(row.get("pe_power"), 1.0)
        
        # Format power and ATR to remove trailing decimals if they are whole numbers
        ce_disp = int(ce_power) if ce_power.is_integer() else ce_power
        pe_disp = int(pe_power) if pe_power.is_integer() else pe_power
        atr_disp = int(atr_val) if atr_val.is_integer() else round(atr_val, 2)

        # 2. Print status line exactly once per refresh cycle using unique data snapshot
        print_key = f"{atr_disp}_{ce_disp}_{pe_disp}"
        if print_key not in printed_sides:
            # Uses the dynamic ATR number inside raw_text to calculate exact centering width
            raw_text = f"↕️ {atr_disp}  🟢  BUY : {ce_disp}%  🔴  SELL: {pe_disp}%"
            spaces_needed = max(0, (40 - len(raw_text)) // 2)
            padding = " " * spaces_needed
            
            # Print perfectly centered output with ANSI text coloring
            print(f"{padding}↕️ {atr_disp}  {Fore.GREEN}🟢  BUY : {ce_disp}%  {Fore.RED}🔴  SELL: {pe_disp}%")
            printed_sides.add(print_key)

        # 3. Entry data health check
        entry_prc = i(row.get("pxy_entry") or row.get("buy_prc"))
        if entry_prc <= 0:
            return 0

        # 4. Context extractors (Get trade direction from Symbol)
        symbol = str(row.get("symbol", "unknown")).upper()
        active_exit = str(row.get("exit", "NONE")).upper().strip()

        is_ce = "CE" in symbol
        is_pe = "PE" in symbol

        if not is_ce and not is_pe:
            return entry_prc

        target_pct = 0.0

        # 5. Core execution logic evaluating directional signals
        if is_ce:
            if active_exit in ["SELL", "BEAR"]:  # Opposite side signal
                target_pct = atr_val
            else:                                # Same side signal
                target_pct = atr_val + ce_power

        elif is_pe:
            if active_exit in ["BUY", "BULL"]:   # Opposite side signal
                target_pct = atr_val
            else:                                # Same side signal
                target_pct = atr_val + pe_power

        # 6. Final mathematical target projection calculation
        calculated_target = entry_prc * (1 + (target_pct / 100.0))
        return round(calculated_target, 2)

    except Exception as e:
        print(f"{Fore.RED}Error in target_price engine: {e}{Style.RESET_ALL}")
        return 0

