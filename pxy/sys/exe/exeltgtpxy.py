
import math
import sys

import pandas as pd
import re
from colorama import Fore, Style, init
from syscnfgpxy import (
    EXETGTPXY_MIN_TARGET_PCT,
    EXETGTPXY_MIN_ATR_VALUE,
    EXETGTPXY_EXIT_KEY_COLUMN,
    EXETGTPXY_MAX_TARGET_CAP,
    EXETGTPXY_MODE,
    EXETGTPXY_STATIC_ALIGNED,
    EXETGTPXY_TGT_PCT_NOT_ALIGNED,
)

# ==================== CONFIG (this file's settings) ====================
EXIT_KEY_COLUMN = EXETGTPXY_EXIT_KEY_COLUMN
MIN_TARGET_PCT = EXETGTPXY_MIN_TARGET_PCT
MIN_ATR_VALUE = EXETGTPXY_MIN_ATR_VALUE
MAX_TARGET_CAP = EXETGTPXY_MAX_TARGET_CAP
TGT_MODE = EXETGTPXY_MODE  # "DYNAMIC" or "STATIC"
STATIC_ALIGNED_PCT = EXETGTPXY_STATIC_ALIGNED
STATIC_NOT_ALIGNED_PCT = EXETGTPXY_TGT_PCT_NOT_ALIGNED
# =======================================================================

init(autoreset=True)

_warned = set()

def _warn_once(key, msg):
    """Prints a warning only the first time it occurs in this process."""
    if key not in _warned:
        _warned.add(key)
        print(f"{Fore.YELLOW}⚠️ {msg}{Style.RESET_ALL}")


# ===== TARGET FORMULA CORE =====

def _target_base_factor(atr, ce_investment, pe_investment, ce_count, pe_count, is_ce):
    """Calculate the existing count-sensitive target base.

    Formula: ATR × (1 + inverse_factor)² × (own_count + 1) / (opposite_count + 1)
    
    Returns a positive value for target calculation.
    """
    if atr <= 0:
        return 0.0
    
    ce_safe = max(ce_investment, 1.0)
    pe_safe = max(pe_investment, 1.0)
    
    if is_ce:
        inverse_factor = 1.0 if (ce_investment <= 0 or pe_investment <= 0) else (ce_safe / pe_safe)
        count_factor = (ce_count + 1) / (pe_count + 1)
    else:
        inverse_factor = 1.0 if (pe_investment <= 0 or ce_investment <= 0) else (pe_safe / ce_safe)
        count_factor = (pe_count + 1) / (ce_count + 1)
    
    base_factor = atr * ((1.0 + inverse_factor) ** 2) * count_factor
    return round(base_factor, 2)


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
    else:
        exponent = ratio * math.log(ratio)
        max_factor = sys.float_info.max / 14.0
        factor = (
            math.exp(exponent)
            if exponent < math.log(max_factor)
            else max_factor
        )
    magnitude = 14.0 * factor
    return -round(magnitude, 2)


def calculate_tgt(atr, ce_investment, pe_investment, ce_count, pe_count, is_ce, is_aligned):
    """Calculates TGT (exit target) percentage.
    
    Aligned: Returns calculated opposite_base_factor + ATR
    Not aligned: Returns fixed 1.4%
    """
    if is_aligned:
        opposite_is_ce = not is_ce
        base = _target_base_factor(
            atr, ce_investment, pe_investment, ce_count, pe_count, opposite_is_ce
        )
        return base + atr
    else:
        return STATIC_NOT_ALIGNED_PCT


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
    """Calculates target price with switchable TGT mode.
    
    MODE: DYNAMIC (Unified Mirror Logic with LGT)
    ================================================
    Formula (ALIGNED):
      target_pct% = calculated opposite_base_factor + ATR, capped at 77%

    Formula (NOT aligned):
      target_pct% = configured fixed percentage (normally 1.4%)
    
    MIRROR LOGIC:
      - CE_LGT uses base_factor negated (for averaging difficulty)
      - PE_TGT uses same base_factor positive + extra ATR (for exit ease) ← MIRROR!
      
    Example: CE=2000 (heavy, 5 layers), PE=1000 (light, 1 layer)
      base_factor ≈ 18.0
      CE_LGT = -18.0 (hard to average)
      PE_TGT = +18.0 + 5.0 = +23.0% (before the 77% cap)
    
    MODE: STATIC (Fixed Percentages)
    ================================
    Formula (ALIGNED):
      target_pct% = 99%
    
    Formula (NOT aligned):
      target_pct% = 1.4%
    
    Args:
        row: dict with 'pxy_entry'/'buy_prc', 'symbol', 'exit', 'atr'
        ce_investment: CE side investment (USD/token)
        pe_investment: PE side investment (USD/token)
        ce_count: CE side layer count
        pe_count: PE side layer count
    
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
        derived_supr = str(row.get(EXIT_KEY_COLUMN, '')).upper().strip()
        
        # Extract and safely cast atr with guardrail
        raw_atr = f(row.get('atr', 0.0))
        if raw_atr <= 0:
            _warn_once(
                "atr",
                f"'atr' missing or <= 0 in row; applying {MIN_ATR_VALUE} minimum ATR.",
            )
        if derived_supr not in ("BULL", "BEAR", "SIDE", "NONE"):
            _warn_once("supertrend", f"unrecognised exit value '{derived_supr}' (expected BULL/BEAR/SIDE/NONE).")
        
        # Apply ATR minimum guardrail
        atr_scaled = max(raw_atr, MIN_ATR_VALUE)

        is_ce = symbol.endswith('CE')
        is_pe = symbol.endswith('PE')
        if not is_ce and not is_pe:
            return round(entry_prc, 2)

        is_aligned = (derived_supr == 'BULL' and is_ce) or (derived_supr == 'BEAR' and is_pe)
        ce_investment = f(ce_investment)
        pe_investment = f(pe_investment)
        # 3️⃣ Apply target formula based on trend status and execution mode
        if derived_supr == 'SIDE':
            target_pct = STATIC_NOT_ALIGNED_PCT  # Flat 1.4% for both CE and PE in SIDE trend
        elif TGT_MODE == "STATIC":
            if is_aligned:
                target_pct = STATIC_ALIGNED_PCT  # 99%
            else:
                target_pct = STATIC_NOT_ALIGNED_PCT  # 1.4%
        else:
            # Dynamic mode (default): Central calculate_tgt helper
            target_pct = calculate_tgt(atr_scaled, ce_investment, pe_investment, ce_count, pe_count, is_ce, is_aligned)

        
        # 4️⃣ Final clamping to [1.4, 99] or [1.4, 77] depending on mode
        max_cap = STATIC_ALIGNED_PCT if TGT_MODE == "STATIC" else MAX_TARGET_CAP
        target_pct_clamped = max(MIN_TARGET_PCT, min(target_pct, max_cap))
        
        # 5️⃣ Calculate target price
        calculated_target = entry_prc * (1.0 + (target_pct_clamped / 100.0))
        return round(calculated_target, 2)
        
    except Exception as e:
        print(f"{Fore.RED}Error in target_price engine: {e}{Style.RESET_ALL}")
        return 0.0
