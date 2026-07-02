# sys/exe/dynentrypxy.py
import pandas as pd
from colorama import Fore, Style, init

# Initialize colorama for clean, colored terminal output formatting
init(autoreset=True)

# Global tracking structures to prevent log flooding on rapid tick cycles
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


def dynamic_entry(row):
    """Returns the raw entry price from row dictionary entries with no tracking variables."""
    try:
        return round(float(row.get("buy_prc", 0)), 2)
    except Exception:
        return 0.0


def target_price(row):
    """Calculates individual option layer target price using dynamic matrices.
    
    Aligned Trades : ((ATR * Same-Side Power) + Same-Side Depth) for maximized exit extraction.
    Hostile Trades : ATR baseline tracking with an absolute 1.0% safety floor.
    """
    global printed_sides

    try:
        # 1. Extract baseline metrics safely
        atr_val = f(row.get("atr"), 6.0)
        
        # 2. Extract Option Matrix parameters (Enforce absolute 1.0 minimum to prevent errors)
        ce_p = max(1.0, f(row.get("ce_power"), 1.0))
        pe_p = max(1.0, f(row.get("pe_power"), 1.0))
        hce_d = max(1.0, f(row.get("hkin_ce_depth"), 1.0))
        hpe_d = max(1.0, f(row.get("hkin_pe_depth"), 1.0))

        # 3. Context string extractors
        symbol = str(row.get("symbol", "unknown")).upper()
        active_exit = str(row.get("exit", "NONE")).upper().strip()

        is_ce = "CE" in symbol
        is_pe = "PE" in symbol

        # 4. SIMULTANEOUS MATRIX EVALUATION (Calculates asking % for both sides)
        # --- Evaluate Call (BUY) Side ---
        if active_exit in ["SELL", "BEAR"]:  # Counter-Trend / Hostile
            ce_target_pct = atr_val
        else:  # Aligned Trend: ((ATR * Same-Side Power) + Same-Side Depth)
            ce_target_pct = (atr_val * ce_p) + hce_d
        ce_target_pct = max(1.0, ce_target_pct)

        # --- Evaluate Put (SELL) Side ---
        if active_exit in ["BUY", "BULL"]:  # Counter-Trend / Hostile
            pe_target_pct = atr_val
        else:  # Aligned Trend: ((ATR * Same-Side Power) + Same-Side Depth)
            pe_target_pct = (atr_val * pe_p) + hpe_d
        pe_target_pct = max(1.0, pe_target_pct)

        # 5. DUAL-SIDE DASHBOARD PRINT LINE
        atr_disp = int(atr_val) if float(atr_val).is_integer() else round(atr_val, 2)
        ce_disp = int(ce_target_pct) if float(ce_target_pct).is_integer() else round(ce_target_pct, 2)
        pe_disp = int(pe_target_pct) if float(pe_target_pct).is_integer() else round(pe_target_pct, 2)

        # Track unique states using both evaluated targets to log live shifts instantly
        print_key = f"{atr_disp}_{ce_disp}_{pe_disp}"
        if print_key not in printed_sides:
            raw_str = f" {atr_disp} BUY : {ce_disp}% SELL: {pe_disp}%"
            spaces = max(0, (40 - len(raw_str) - 6) // 2)
            print(f"{' ' * spaces}↕️ {atr_disp} {Fore.GREEN}🟢 BUY : {ce_disp}% {Fore.RED}🔴 SELL: {pe_disp}%")
            printed_sides.add(print_key)

        # 6. Entry data execution health check
        entry_prc = f(row.get("pxy_entry") or row.get("buy_prc"))
        if entry_prc <= 0:
            return 0.0

        if not is_ce and not is_pe:
            return round(entry_prc, 2)

        # 7. Final mathematical target premium projection calculation
        final_pct = ce_target_pct if is_ce else pe_target_pct
        calculated_target = entry_prc * (1 + (final_pct / 100.0))
        return round(calculated_target, 2)

    except Exception as e:
        print(f"{Fore.RED}Error in target_price engine: {e}{Style.RESET_ALL}")
        return 0.0

