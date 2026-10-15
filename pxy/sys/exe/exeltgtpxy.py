#!/usr/bin/env python3
import math
import pandas as pd
import re
import sys
from pathlib import Path
from colorama import Fore, Style, init

# ----------------- PATH FIX FOR INDEPENDENT RUNNING -----------------
HERE = Path(__file__).resolve().parent          # /home/pxy/PXY/pxy/sys/exe
SYS_DIR = HERE.parent                            # /home/pxy/PXY/pxy/sys
PXY_DIR = SYS_DIR.parent                         # /home/pxy/PXY/pxy

# Explicitly add all base paths to sys.path so files can find each other
for path in (SYS_DIR, PXY_DIR, HERE):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from syscnfgpxy import (
    EXEAMSPXY_MAX_LGT_LOSS,
    EXEAGTPXY_SYSTEM_B_BASE_THRESHOLD,
    EXETGTPXY_EXIT_KEY_COLUMN,
    EXETGTPXY_TGT_PCT_NOT_ALIGNED,
)

# ==================== CONFIG (this file's settings) ====================
EXIT_KEY_COLUMN = EXETGTPXY_EXIT_KEY_COLUMN
NOT_ALIGNED_TARGET_PCT = EXETGTPXY_TGT_PCT_NOT_ALIGNED
BOTH_SIDES_ALIGNED_TARGET_PCT = 77.0
# =======================================================================

init(autoreset=True)

_warned = set()

def _warn_once(key, msg):
    """Prints a warning only the first time it occurs in this process."""
    if key not in _warned:
        _warned.add(key)
        print(f"{Fore.YELLOW}⚠️ {msg}{Style.RESET_ALL}")


def calculate_lgt(ce_investment, pe_investment, is_ce, index_price):
    """Calculate the capped LGT percentage from the relative investments."""
    try:
        index_price = float(index_price)
    except (TypeError, ValueError) as error:
        raise ValueError("index_price must be a finite positive number.") from error
    if not math.isfinite(index_price) or index_price <= 0:
        raise ValueError("index_price must be a finite positive number.")

    own_investment, opposite_investment = (
        (ce_investment, pe_investment) if is_ce else (pe_investment, ce_investment)
    )
    try:
        own_investment = float(own_investment)
        opposite_investment = float(opposite_investment)
    except (TypeError, ValueError, OverflowError):
        ratio = 1.0
    else:
        ratio_is_valid = (
            math.isfinite(own_investment)
            and math.isfinite(opposite_investment)
            and own_investment > 0
            and opposite_investment > 0
        )
        if ratio_is_valid:
            ratio = own_investment / opposite_investment
            ratio_is_valid = math.isfinite(ratio)
            if ratio_is_valid:
                ratio = min(10.0, max(0.1, ratio))
        if not ratio_is_valid:
            ratio = 1.0
    magnitude = max(
        EXEAGTPXY_SYSTEM_B_BASE_THRESHOLD,
        round(66.0 * ratio, 2),
    )
    return -min(magnitude, EXEAMSPXY_MAX_LGT_LOSS)


def calculate_tgt(
    is_aligned,
    atr=None,
    side_power=None,
    side_depth=None,
    both_sides_open=False,
    heavy_side=False,
):
    """Return a fixed 77% aligned target, otherwise the non-aligned target."""
    return BOTH_SIDES_ALIGNED_TARGET_PCT if is_aligned else NOT_ALIGNED_TARGET_PCT


def f(x, d=0.0):
    """Safely casts input to float, returning a default value if casting fails or value <= 0."""
    try:
        val = float(x)
        return val if val > 0 else d
    except (ValueError, TypeError):
        return d

def compute_market_exposure(df: pd.DataFrame) -> tuple[float, float]:
    """Calculates CE and PE exposure globally ONCE to prevent row iteration lag."""
    if df is None or df.empty:
        return 0.0, 0.0
        
    symbols = df['symbol'].astype(str).str.upper()
    qtys = pd.to_numeric(df['qty'], errors='coerce').fillna(0).clip(lower=0)
    prices = pd.to_numeric(df['sell_prc'], errors='coerce').fillna(0).clip(lower=0)
    
    invested = qtys * prices
    
    is_ce = symbols.str.strip().str.endswith('CE')
    is_pe = symbols.str.strip().str.endswith('PE')
    
    ce_total = float(invested[is_ce].sum())
    pe_total = float(invested[is_pe].sum())
    
    return ce_total, pe_total

def target_price(row, ce_investment: float = 0.0, pe_investment: float = 0.0, ce_count: int = 0, pe_count: int = 0):
    """Calculate the target from exit alignment and the open side counts."""
    try:
        entry_prc = f(row.get('pxy_entry') or row.get('buy_prc'))
        if entry_prc <= 0:
            return 0.0
            
        symbol = str(row.get('symbol', 'UNKNOWN')).upper().strip()
        exit_signal = str(row.get(EXIT_KEY_COLUMN, '')).upper().strip()
        if exit_signal not in ("BULL", "BEAR", "SIDE", "NONE"):
            _warn_once("exit", f"unrecognised exit value '{exit_signal}' (expected BULL/BEAR/SIDE/NONE).")

        is_ce = symbol.endswith('CE')
        is_pe = symbol.endswith('PE')
        if not is_ce and not is_pe:
            return round(entry_prc, 2)

        is_aligned = (
            (exit_signal == "BULL" and is_ce)
            or (exit_signal == "BEAR" and is_pe)
        )
        both_sides_open = ce_count > 0 and pe_count > 0
        heavy_side = (
            ce_investment > pe_investment
            if is_ce
            else pe_investment > ce_investment
        )
        side_power = row.get("ce_power" if is_ce else "pe_power")
        side_depth = row.get("hkin_ce_depth" if is_ce else "hkin_pe_depth")
        
        target_pct = calculate_tgt(
            is_aligned,
            atr=row.get("atr"),
            side_power=side_power,
            side_depth=side_depth,
            both_sides_open=both_sides_open,
            heavy_side=heavy_side,
        )
        
        calculated_target = entry_prc * (1.0 + (target_pct / 100.0))
        return round(calculated_target, 2)
        
    except Exception as e:
        print(f"{Fore.RED}Error in target_price engine: {e}{Style.RESET_ALL}")
        return 0.0

