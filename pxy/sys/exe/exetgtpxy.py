from datetime import datetime
from colorama import Fore, Style, init
import pytz

init(autoreset=True)
ist = pytz.timezone("Asia/Kolkata")

# Global set to track printed sides for the current refresh cycle
printed_sides = set()


def f(x, d=0.0):
    try:
        val = float(x)
        return val if val > 0 else d
    except Exception:
        return d


def i(x, d=0):
    try:
        return int(float(x))
    except Exception:
        return d


def target_price(row):
    global printed_sides

    try:
        # 1. Entry data health check
        entry_prc = i(row.get("pxy_entry") or row.get("buy_prc"))

        if entry_prc <= 0:
            return 0

        # 2. Extract spread volatility layer data
        atr_val = f(row.get("atr"), 6.0)

        # 3. Context extractors (Get trade direction from Symbol)
        symbol = str(row.get("symbol", "unknown")).upper()

        is_ce = "CE" in symbol
        is_pe = "PE" in symbol

        if not is_ce and not is_pe:
            return entry_prc

        # Ingest parameter context flags directly from your row dictionary keys
        is_counter = str(row.get("counter", "n")).upper().strip() == "Y"

        # Read the raw, unfiltered Exit Signal from upstream data stream
        active_exit = str(row.get("exit", "NONE")).upper().strip()

        # 4. Capture structural multiplier fields (power)
        ce_power = f(row.get("ce_power"), 1.0)
        pe_power = f(row.get("pe_power"), 1.0)

        # 5. Core execution logic evaluating multi-value directional signals
        target_pct = 0.0

        if is_ce:
            # RULE: Signal flip (opposite direction) falls back to exactly 2.8
            if active_exit in ["SELL", "BEAR"]:
                target_pct = 2.8
            
            # RULE: Counter trade scaling = ATR * power
            elif is_counter:
                target_pct = atr_val / 2
            
            # RULE: No counter scaling = Base ATR only
            else:
                target_pct = atr_val

        elif is_pe:
            # RULE: Signal flip (opposite direction) falls back to exactly 2.8
            if active_exit in ["BUY", "BULL"]:
                target_pct = 2.8
            
            # RULE: Counter trade scaling = ATR * power
            elif is_counter:
                target_pct = atr_val / 2
            
            # RULE: No counter scaling = Base ATR only
            else:
                target_pct = atr_val

        # --- ABSOLUTE SAFETY FLOOR PROTECTION ---
        # Guarantees that target_pct is never less than 2.8 under any circumstance
        if target_pct < 2.8:
            target_pct = 2.8

        # 6. Final mathematical target projection calculation
        calculated_target = entry_prc * (1 + (target_pct / 100.0))

        return round(calculated_target, 2)

    except Exception as e:
        print(
            f"{Fore.RED}Error in target_price matrix engine: "
            f"{e}{Style.RESET_ALL}"
        )
        return 0

