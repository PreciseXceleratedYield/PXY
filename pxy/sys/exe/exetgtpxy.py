"""
===============================================================================
PXY AUTOMATED TARGET PRICE MATRIX ENGINE - USER GUIDE (LAYMAN TERMS)
===============================================================================

WHAT THIS SCRIPT DOES:
This script automatically calculates the "Target Price" (take-profit price)
for options trading positions based strictly on the status of your Exit Signal.

HOW EXIT SIGNALS TRIGGER EMERGENCY CHECKS:
- CALL OPTIONS (CE) Mode: Swaps to emergency mode if Exit Signal is "SELL" or "BEAR".
- PUT OPTIONS (PE) Mode:  Swaps to emergency mode if Exit Signal is "BUY" or "BULL".

HOW THE CHOSEN TARGET IS DECIDED (THE 3 SCENARIOS):
1. NORMAL TRADING:
   - Target Percentage = Market Volatility (ATR) × Its Relevant Power.

2. COUNTER-TREND TRADING (Safety Hold):
   - If marked as a 'Counter' trade, the target is capped at +99% to hold.

3. OPPOSITE EXIT SIGNAL FIRED (Emergency Exit Filter):
   - If an opposite exit signal fires, the system checks the current expected return.
   - If that value is 1.4% or higher, it allows the exit target to be created.
   - If it is below 1.4%, it locks the target at +99% to hold flat
     and prevent accidental market order liquidations.

REQUIRED DATA INPUTS (What needs to be in your 'row' data):
- symbol: The name of the option contract (must contain 'CE' or 'PE').
- buy_prc / pxy_entry: The price you bought into the trade.
- atr: Market volatility indicator (Average True Range).
- counter: Set to 'Y' if this is a counter-trend trade.
- exit: The active market exit signal ('BUY', 'SELL', 'BULL', 'BEAR', or 'NONE').
- ce_power / pe_power: The relevant strength multiplier for the option type.

OUTPUT:
- Returns the exact mathematical target price as a clean decimal number.
- Returns 0 if data is missing, broken, or invalid.
===============================================================================
"""

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
        is_counter = str(
            row.get("counter", "n")
        ).upper().strip() == "Y"

        # Read the raw, unfiltered Exit Signal from upstream data stream
        active_exit = str(
            row.get("exit", "NONE")
        ).upper().strip()

        # 4. Capture structural multiplier fields
        ce_p = f(row.get("ce_power"), 1.0)
        pe_p = f(row.get("pe_power"), 1.0)

        # Pre-compute local market yield definitions: ATR * relevant power only
        ce_yield = atr_val * ce_p
        pe_yield = atr_val * pe_p

        # 5. Core execution logic evaluating multi-value exit signals
        target_pct = 0.0

        if is_ce:

            if active_exit in ["SELL", "BEAR"]:
                target_pct = ce_yield if ce_yield >= 1.4 else 99.0

            elif is_counter:
                target_pct = 99.0

            else:
                target_pct = ce_yield

        elif is_pe:

            if active_exit in ["BUY", "BULL"]:
                target_pct = pe_yield if pe_yield >= 1.4 else 99.0

            elif is_counter:
                target_pct = 99.0

            else:
                target_pct = pe_yield

        # 6. Final mathematical target projection calculation
        calculated_target = entry_prc * (1 + (target_pct / 100.0))

        return round(calculated_target, 2)

    except Exception as e:
        print(
            f"{Fore.RED}Error in target_price matrix engine: "
            f"{e}{Style.RESET_ALL}"
        )
        return 0
