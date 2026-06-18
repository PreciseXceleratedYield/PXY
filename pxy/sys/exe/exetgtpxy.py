# sys/exe/dynentrypxy.py
from datetime import datetime
import re
import pandas as pd
from colorama import Fore, Style, init
import pytz

# Initialize colorama for colored terminal output
init(autoreset=True)
IST = pytz.timezone("Asia/Kolkata")

# Global tracking structures
printed_sides = set()
_worst_trades = {
    "CE": {"elapsed_hours": -1.0, "message": None},
    "PE": {"elapsed_hours": -1.0, "message": None}
}

# ==================================================
# 🔧 REVISED CONFIG: COMPRESSION DETECTOR TIME DECAY
# ==================================================
DECAY_RATE_PER_HOUR = 0.02  # 2% decay per hour
PNL_THRESHOLD = 0.0


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
    """Calculates time-decay on entry prices and tracks the worst CE/PE records."""
    global _worst_trades
    try:
        original_price = float(row.get("buy_prc", 0))
        entry_time_val = row.get("buy_time")
        symbol = str(row.get("symbol", "")).upper()
        pnl = float(row.get("pnl", 0))
        
        if not entry_time_val or original_price <= 0:
            return original_price
            
        now = datetime.now(IST)

        # ---------------- PARSE ENTRY TIME ----------------
        if isinstance(entry_time_val, str):
            try:
                entry_time = datetime.strptime(entry_time_val, "%Y-%m-%d %H:%M:%S")
                entry_time = IST.localize(entry_time)
            except:
                parts = list(map(int, str(entry_time_val).split(":")[-3:]))
                entry_time = now.replace(hour=parts[0], minute=parts[1], second=parts[2], microsecond=0)
        else:
            entry_time = pd.to_datetime(entry_time_val)
            if entry_time.tzinfo is None:
                entry_time = IST.localize(entry_time)
            else:
                entry_time = entry_time.astimezone(IST)

        # ---------------- CALC ELAPSED HOURS ----------------
        elapsed_secs = max((now - entry_time).total_seconds(), 0)
        elapsed_hours = elapsed_secs / 3600.0 

        # ---------------- PERCENTAGE DECAY RULE ----------------
        if pnl <= PNL_THRESHOLD:
            total_decay_percentage = elapsed_hours * DECAY_RATE_PER_HOUR
            dynamic_val = original_price * (1.0 - total_decay_percentage)
            dynamic_val = max(dynamic_val, 0.0)
            
            decay_amount = original_price - dynamic_val
            pct_given_away = total_decay_percentage * 100.0
            
            # Determine Option Type
            opt_type = None
            if "CE" in symbol:
                opt_type = "CE"
            elif "PE" in symbol:
                opt_type = "PE"
                
            # Track worst trade independently for CE and PE
            if opt_type and decay_amount > 0.05 and elapsed_hours > _worst_trades[opt_type]["elapsed_hours"]:
                clean_symbol = re.sub(r'^(NIFTY|BANKNIFTY)26', '', symbol)
                _worst_trades[opt_type]["elapsed_hours"] = elapsed_hours
                _worst_trades[opt_type]["message"] = (
                    f"{Fore.YELLOW}⚠️ WORST {opt_type} | {clean_symbol} | "
                    f"GAVE AWAY: {pct_given_away:.1f}% (-{decay_amount:.2f} PTS) | "
                    f"ELAPSED: {elapsed_hours:.2f} hrs{Style.RESET_ALL}"
                )
        else:
            dynamic_val = original_price
            
        return round(dynamic_val, 2)
        
    except Exception as e:
        print(f"Error in dynamic_entry: {e}")
        return original_price


def print_oldest_decay():
    """Prints the worst decayed CE and PE trades, then flushes runtime memory."""
    global _worst_trades
    
    if _worst_trades["CE"]["message"] is not None:
        print(_worst_trades["CE"]["message"])
        
    if _worst_trades["PE"]["message"] is not None:
        print(_worst_trades["PE"]["message"])
        
    # Reset internal memory block
    _worst_trades = {
        "CE": {"elapsed_hours": -1.0, "message": None},
        "PE": {"elapsed_hours": -1.0, "message": None}
    }


def target_price(row):
    """Calculated target price based strictly on ATR and signal direction."""
    global printed_sides

    try:
        # 1. Extract base values and powers needed for printing and logic
        atr_val = f(row.get("atr"), 6.0)
        ce_power = f(row.get("ce_power"), 1.0)
        pe_power = f(row.get("pe_power"), 1.0)
        
        ce_disp = int(ce_power) if float(ce_power).is_integer() else ce_power
        pe_disp = int(pe_power) if float(pe_power).is_integer() else pe_power
        atr_disp = int(atr_val) if float(atr_val).is_integer() else round(atr_val, 2)

        # 2. Print status line exactly once per refresh cycle using unique data snapshot
        print_key = f"{atr_disp}_{ce_disp}_{pe_disp}"
        if print_key not in printed_sides:
            raw_display_len = len(f" {atr_disp}    BUY : {ce_disp}%    SELL: {pe_disp}%") + 6  
            spaces_needed = max(0, (40 - raw_display_len) // 2)
            padding = " " * spaces_needed
            
            print(f"{padding}↕️ {atr_disp}  {Fore.GREEN}🟢  BUY : {ce_disp}%  {Fore.RED}🔴  SELL: {pe_disp}%")
            printed_sides.add(print_key)
            
            # --- FIX: We link decay print to the UI refresh to guarantee it fires ---
            print_oldest_decay()

        # 3. Entry data health check
        entry_prc = i(row.get("pxy_entry") or row.get("buy_prc"))
        if entry_prc <= 0:
            return 0

        # 4. Context extractors
        symbol = str(row.get("symbol", "unknown")).upper()
        active_exit = str(row.get("exit", "NONE")).upper().strip()

        is_ce = "CE" in symbol
        is_pe = "PE" in symbol

        if not is_ce and not is_pe:
            return entry_prc

        target_pct = 0.0

        # 5. Core execution logic evaluating directional signals
        if is_ce:
            if active_exit in ["SELL", "BEAR"]:  
                target_pct = 1.4 
            else:                                
                target_pct = 1.4  * ce_power 

        elif is_pe:
            if active_exit in ["BUY", "BULL"]:   
                target_pct = 1.4 
            else:                                
                target_pct = 1.4 * pe_power 

        # 6. Final mathematical target projection calculation
        calculated_target = entry_prc * (1 + (target_pct / 100.0))
        return round(calculated_target, 2)

    except Exception as e:
        print(f"{Fore.RED}Error in target_price engine: {e}{Style.RESET_ALL}")
        return 0

