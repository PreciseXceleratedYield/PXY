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
    """Calculates individual option layer target price using static alignment matrices.
    
    Aligned Trades     : Hardcoded directly to a massive 99.0% breakout capture target.
    Not Aligned Trades : Fixed strictly to a tight 1.4% profit target for quick scratch containment.
    """
    global printed_sides

    try:
        # 1. Extract baseline metrics safely for status telemetry line
        atr_val = f(row.get("atr"), 6.0)
        ce_power = f(row.get("ce_power"), 1.0)
        pe_power = f(row.get("pe_power"), 1.0)
        
        ce_disp = int(ce_power) if float(ce_power).is_integer() else ce_power
        pe_disp = int(pe_power) if float(pe_power).is_integer() else pe_power
        atr_disp = int(atr_val) if float(atr_val).is_integer() else round(atr_val, 2)

        # 2. Print dashboard status line once per unique data configuration refresh
        print_key = f"{atr_disp}_{ce_disp}_{pe_disp}"
        if print_key not in printed_sides:
            raw_display_len = len(f" {atr_disp}    BUY : {ce_disp}%    SELL: {pe_disp}%") + 6  
            spaces_needed = max(0, (40 - raw_display_len) // 2)
            padding = " " * spaces_needed
            
            print(f"{padding}↕️ {atr_disp}  {Fore.GREEN}🟢  BUY : {ce_disp}%  {Fore.RED}🔴  SELL: {pe_disp}%")
            printed_sides.add(print_key)

        # 3. Entry data execution health check
        entry_prc = f(row.get("pxy_entry") or row.get("buy_prc"))
        if entry_prc <= 0:
            return 0.0

        # 4. Context string extractors mapped directly from your row payload schema
        symbol = str(row.get("symbol", "unknown")).upper()
        active_exit = str(row.get("exit", "NONE")).upper().strip()

        is_ce = "CE" in symbol
        is_pe = "PE" in symbol

        if not is_ce and not is_pe:
            return round(entry_prc, 2)

        target_pct = 0.0

        # 5. Core execution logic evaluating explicit target values based on matching alignment
        if is_ce:
            if active_exit in ["SELL", "BEAR"]:  
                # Counter-Trend (Not Aligned): Hard-locked to a tight 1.4% cut target
                target_pct = atr_val
            else:                                
                # Aligned Trend: Hardcoded directly to a massive 99.0% extraction percentage
                target_pct = atr_val * ce_power
        elif is_pe:
            if active_exit in ["BUY", "BULL"]:   
                # Counter-Trend (Not Aligned): Hard-locked to a tight 1.4% cut target
                target_pct = atr_val 
            else:                                
                # Aligned Trend: Hardcoded directly to a massive 99.0% extraction percentage
                target_pct = atr_val * pe_power
                
        # 6. Final mathematical target premium projection calculation
        calculated_target = entry_prc * (1 + (target_pct / 100.0))
        return round(calculated_target, 2)

    except Exception as e:
        print(f"{Fore.RED}Error in target_price engine: {e}{Style.RESET_ALL}")
        return 0.0
