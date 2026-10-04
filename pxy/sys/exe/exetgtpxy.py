
import pandas as pd
import re
from colorama import Fore, Style, init
from syscnfgpxy import (
    EXETGTPXY_ATR_FLOOR,
    EXETGTPXY_ATR_MIN,
    EXETGTPXY_EXIT_KEY_COLUMN,
    EXETGTPXY_MAX_TARGET_CAP,
)

# ==================== CONFIG (this file's settings) ====================
EXIT_KEY_COLUMN = EXETGTPXY_EXIT_KEY_COLUMN
ATR_FLOOR = EXETGTPXY_ATR_FLOOR
ATR_MIN = EXETGTPXY_ATR_MIN
MAX_TARGET_CAP = EXETGTPXY_MAX_TARGET_CAP
                               # (same rule as is_aligned in exeagtpxy.py); SIDE / NONE / unknown = not aligned
# =======================================================================

# Initialize colorama for clean, colored terminal output formatting
init(autoreset=True)

_warned = set()

def _warn_once(key, msg):
    """Prints a warning only the first time it occurs in this process."""
    if key not in _warned:
        _warned.add(key)
        print(f"{Fore.YELLOW}⚠️ target_price: {msg}{Style.RESET_ALL}")

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

def target_price(row, ce_investment: float = 0.0, pe_investment: float = 0.0):
    """Calculates target price using investment-factor-scaled ATR.
    
    Formula:
      NOT aligned: target_pct = max(ATR × inverse_factor, 1.4%)
      ALIGNED:     target_pct = 77%
    
    Where inverse_factor = opposite_investment / current_investment
    (defaults to 1.0 if opposite = 0, creating lighter-side penalty)
    
    Args:
        row: dict with 'pxy_entry'/'buy_prc', 'symbol', 'exit', 'atr'
        ce_investment: CE side investment (USD/token)
        pe_investment: PE side investment (USD/token)
    
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
            _warn_once("atr", f"'atr' missing or <= 0 in row; using {ATR_FLOOR} floor.")
        if derived_supr not in ("BULL", "BEAR", "SIDE", "NONE"):
            _warn_once("supertrend", f"unrecognised exit value '{derived_supr}' (expected BULL/BEAR/SIDE/NONE).")
        
        # Apply ATR minimum guardrail
        atr_scaled = max(raw_atr, ATR_MIN)

        is_ce = symbol.endswith('CE')
        is_pe = symbol.endswith('PE')
        if not is_ce and not is_pe:
            return round(entry_prc, 2)

        # 3️⃣ Calculate investment factor (opposite / current)
        ce_safe = ce_investment if ce_investment > 0 else 1.0
        pe_safe = pe_investment if pe_investment > 0 else 1.0
        
        if is_ce:
            # CE is current side
            inverse_factor = pe_safe / ce_safe
            is_aligned = (derived_supr == 'BULL')
        else:
            # PE is current side
            inverse_factor = ce_safe / pe_safe
            is_aligned = (derived_supr == 'BEAR')
        
        # 4️⃣ Apply target formula
        if is_aligned:
            # Aligned: use max cap
            target_pct = MAX_TARGET_CAP
        else:
            # Not aligned: scale ATR by inverse factor with 1.4% floor
            target_pct = max(atr_scaled * inverse_factor, ATR_FLOOR)
        
        # 5️⃣ Final clamping to [1.4, 77]
        target_pct_clamped = max(ATR_FLOOR, min(target_pct, MAX_TARGET_CAP))
        
        # 6️⃣ Calculate target price
        calculated_target = entry_prc * (1.0 + (target_pct_clamped / 100.0))
        return round(calculated_target, 2)
        
    except Exception as e:
        print(f"{Fore.RED}Error in target_price engine: {e}{Style.RESET_ALL}")
        return 0.0
