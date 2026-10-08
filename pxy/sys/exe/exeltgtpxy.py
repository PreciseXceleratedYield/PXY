
import math

import pandas as pd
import re
from colorama import Fore, Style, init
from syscnfgpxy import (
    EXEAMSPXY_MAX_LGT_LOSS,
    EXEAGTPXY_SYSTEM_B_BASE_THRESHOLD,
    EXETGTPXY_ALIGNED_PCT,
    EXETGTPXY_EXIT_KEY_COLUMN,
    EXETGTPXY_TGT_PCT_NOT_ALIGNED,
)

# ==================== CONFIG (this file's settings) ====================
EXIT_KEY_COLUMN = EXETGTPXY_EXIT_KEY_COLUMN
ALIGNED_TARGET_PCT = EXETGTPXY_ALIGNED_PCT
NOT_ALIGNED_TARGET_PCT = EXETGTPXY_TGT_PCT_NOT_ALIGNED
# =======================================================================

init(autoreset=True)

_warned = set()

def _warn_once(key, msg):
    """Prints a warning only the first time it occurs in this process."""
    if key not in _warned:
        _warned.add(key)
        print(f"{Fore.YELLOW}⚠️ {msg}{Style.RESET_ALL}")


def calculate_lgt(ce_investment, pe_investment, is_ce):
    """Calculate the negative LGT threshold from the side investment ratio."""
    own_investment, opposite_investment = (
        (ce_investment, pe_investment) if is_ce else (pe_investment, ce_investment)
    )
    ratio = (
        own_investment / opposite_investment
        if own_investment > 0 and opposite_investment > 0
        else 1.0
    )
    if ratio < 1.0:
        factor = ratio**2
        magnitude = max(
            EXEAGTPXY_SYSTEM_B_BASE_THRESHOLD,
            round(20.0 * factor - 2.8, 2),
        )
    else:
        exponent = ratio * math.log(ratio)
        max_factor = EXEAMSPXY_MAX_LGT_LOSS / 20.0
        factor = (
            math.exp(exponent)
            if exponent < math.log(max_factor)
            else max_factor
        )
        magnitude = min(round(20.0 * factor, 2), EXEAMSPXY_MAX_LGT_LOSS)
    return -magnitude


def calculate_tgt(is_aligned):
    """Return the single-mode positive target for the side's trend alignment."""
    return ALIGNED_TARGET_PCT if is_aligned else NOT_ALIGNED_TARGET_PCT


def f(x, d=0.0):
    """Safely casts input to float, returning a default value if casting fails or value <= 0."""
    try:
        val = float(x)
        return val if val > 0 else d
    except (ValueError, TypeError):
        return d

def compute_market_exposure(df: pd.DataFrame) -> tuple[float, float]:
    """Calculates CE and PE exposure globally ONCE to prevent row iteration lag.
    
    Processes the entire DataFrame using fast, vectorized operations.
    """
    if df is None or df.empty:
        return 0.0, 0.0
        
    # Vectorized string conversion and numeric cleanup
    symbols = df['symbol'].astype(str).str.upper()
    qtys = pd.to_numeric(df['qty'], errors='coerce').fillna(0).clip(lower=0)
    prices = pd.to_numeric(df['sell_prc'], errors='coerce').fillna(0).clip(lower=0)
    
    # Calculate row-level dollar / token exposure
    invested = qtys * prices
    
    # Precise substring flags instead of brittle character slicing
    is_ce = symbols.str.strip().str.endswith('CE')
    is_pe = symbols.str.strip().str.endswith('PE')
    
    ce_total = float(invested[is_ce].sum())
    pe_total = float(invested[is_pe].sum())
    
    return ce_total, pe_total

def target_price(row, ce_investment: float = 0.0, pe_investment: float = 0.0, ce_count: int = 0, pe_count: int = 0):
    """Calculate the target using only the configured exit signal and option side.

    Args:
        row: dict containing entry, symbol, and exit. Extra exposure arguments are
        accepted for compatibility but do not affect the target.
    
    Returns:
        float: Target price rounded to 2 decimals
    """
    try:
        # 1️⃣ Entry data execution health check
        entry_prc = f(row.get('pxy_entry') or row.get('buy_prc'))
        if entry_prc <= 0:
            return 0.0
            
        # 2️⃣ Context parameter extractors
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
        target_pct = calculate_tgt(is_aligned)
        target_pct_clamped = max(
            NOT_ALIGNED_TARGET_PCT,
            min(target_pct, ALIGNED_TARGET_PCT),
        )
        
        # Calculate the positive target price.
        calculated_target = entry_prc * (1.0 + (target_pct_clamped / 100.0))
        return round(calculated_target, 2)
        
    except Exception as e:
        print(f"{Fore.RED}Error in target_price engine: {e}{Style.RESET_ALL}")
        return 0.0
