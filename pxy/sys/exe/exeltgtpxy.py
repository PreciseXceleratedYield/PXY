#!/usr/bin/env python3
import sys
from pathlib import Path
from datetime import datetime, time as dt_time

# ----------------- PATH FIX (MUST BE AT ABSOLUTE TOP) -----------------
HERE = Path(__file__).resolve().parent          # /home/pxy/PXY/pxy/sys/exe
SYS_DIR = HERE.parent                            # /home/pxy/PXY/pxy/sys
PXY_DIR = SYS_DIR.parent                         # /home/pxy/PXY/pxy

# Prioritize SYS_DIR (parent directory) so Python finds all sys*.py files first
for path in (SYS_DIR, PXY_DIR, HERE):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

# ----------------- NOW IMPORTS LOAD FLAWLESSLY -----------------
import math
import pandas as pd
import re
from datetime import datetime
from colorama import Fore, Style, init

from syscnfgpxy import (
    EXEAGTPXY_SYSTEM_B_BASE_THRESHOLD,
    EXETGTPXY_EARLY_ALIGNED_TARGET_PCT,
    EXETGTPXY_ALIGNED_MIN_DEPTH,
    EXETGTPXY_EXIT_KEY_COLUMN,
    SYSCNFGPXY_TIMEZONE,
    SYSENTRPXY_ST_START,
)

# ==================== CONFIG (this file's settings) ====================
EXIT_KEY_COLUMN = EXETGTPXY_EXIT_KEY_COLUMN
ALIGNED_MIN_DEPTH = EXETGTPXY_ALIGNED_MIN_DEPTH
EARLY_ALIGNED_TARGET_PCT = EXETGTPXY_EARLY_ALIGNED_TARGET_PCT
# =======================================================================

init(autoreset=True)

_warned = set()

def _warn_once(key, msg):
    """Prints a warning only the first time it occurs in this process."""
    if key not in _warned:
        _warned.add(key)
        print(f"{Fore.YELLOW}⚠️ {msg}{Style.RESET_ALL}")


# === SURGICAL CHANGE START (Error Fallbacks Added) ===
def calculate_lgt(is_aligned, ce_count=0, pe_count=0, is_ce=True):
    """Calculate the simplified negative LGT percentage with an error fallback of -75.0."""
    try:
        own_count = float(ce_count if is_ce else pe_count)
        
        # Core baseline calculation
        base_magnitude = 40.0 + (10.0 * own_count)
        
        # Scale up if it is not aligned
        if not is_aligned:
            base_magnitude *= 1.4
            
        return -base_magnitude
    except Exception as e:
        _warn_once("lgt_err", f"Error in calculate_lgt: {e}. Falling back to -75.0")
        return -75.0


def calculate_tgt(
    is_aligned,
    atr=None,
    side_power=None,
    side_depth=None,
    both_sides_open=False,
    heavy_side=False,
    target_time=None,
):
    """Return target percentage based on alignment status with an error fallback of 25.0."""
    try:
        current_time = target_time
        if current_time is None:
            current_time = datetime.now(SYSCNFGPXY_TIMEZONE)

        if hasattr(current_time, "time"):
            current_time = current_time.time()

        if dt_time(15, 10) <= current_time <= dt_time(15, 30):
            return 99.0

        if not is_aligned:
            return 1.4

        def positive_factor(value):
            try:
                parsed = float(value)
            except (TypeError, ValueError, OverflowError):
                return 1.0
            return parsed if math.isfinite(parsed) and parsed > 0 else 1.0

        own_depth = positive_factor(side_depth)
        own_power = positive_factor(side_power)

        return (14 * (own_depth + own_power)) ** own_power
    except Exception as e:
        _warn_once("tgt_err", f"Error in calculate_tgt: {e}. Falling back to 25.0")
        return 25.0
# === SURGICAL CHANGE END ===


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

def target_price(
    row,
    ce_investment: float = 0.0,
    pe_investment: float = 0.0,
    ce_count: int = 0,
    pe_count: int = 0,
    target_time=None,
):
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
        
        target_pct = calculate_tgt(
            is_aligned,
            atr=row.get("atr"),
            side_power=row.get("ce_power" if is_ce else "pe_power"),
            side_depth=row.get("hkin_ce_depth" if is_ce else "hkin_pe_depth"),
            both_sides_open=(ce_count > 0 and pe_count > 0),
            heavy_side=(ce_investment > pe_investment if is_ce else pe_investment > ce_investment),
            target_time=target_time,
        )
        
        calculated_target = entry_prc * (1.0 + (target_pct / 100.0))
        return round(calculated_target, 2)
        
    except Exception as e:
        print(f"{Fore.RED}Error in target_price engine: {e}{Style.RESET_ALL}")
        return 0.0
