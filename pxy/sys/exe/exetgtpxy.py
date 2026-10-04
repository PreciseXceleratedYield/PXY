
import pandas as pd
import re
from colorama import Fore, Style, init
from syscnfgpxy import (
    EXEAGTPXY_ABS_CAP,
    EXETGTPXY_ATR_FLOOR,
    EXETGTPXY_EXIT_KEY_COLUMN,
    EXETGTPXY_TGT_PCT_NOT_ALIGNED,
)

# ==================== CONFIG (this file's settings) ====================
EXIT_KEY_COLUMN = EXETGTPXY_EXIT_KEY_COLUMN
ATR_FLOOR = EXETGTPXY_ATR_FLOOR
TGT_PCT_NOT_ALIGNED = EXETGTPXY_TGT_PCT_NOT_ALIGNED
COUNTER_SIGNAL_MAX_BALANCE = EXEAGTPXY_ABS_CAP
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
    """Calculates target price by isolating explicit opposite trend exit threats.
    
    Perfectly safe and clean for low row counts (e.g., ~10 rows per calculation).
    """
    try:
        # 1️⃣ Entry data execution health check
        entry_prc = f(row.get('pxy_entry') or row.get('buy_prc'))
        if entry_prc <= 0:
            return 0.0
            
        # 2️⃣ Context parameter extractors
        symbol = str(row.get('symbol', 'UNKNOWN')).upper().strip()
        derived_supr = str(row.get(EXIT_KEY_COLUMN, '')).upper().strip()
        
        # Extract and safely cast atr (will scale safely even if identical across rows)
        raw_atr = f(row.get('atr', 0.0))
        if raw_atr <= 0:
            _warn_once("atr", f"'atr' missing or <= 0 in row (check market column names/case); using {ATR_FLOOR} floor.")
        if derived_supr not in ("BULL", "BEAR", "SIDE", "NONE"):
            _warn_once("supertrend", f"unrecognised exit value '{derived_supr}' (expected BULL/BEAR/SIDE/NONE).")
        atr = max(raw_atr, ATR_FLOOR)

        is_ce = symbol.endswith('CE')
        is_pe = symbol.endswith('PE')
        if not is_ce and not is_pe:
            return round(entry_prc, 2)

        # When no investment imbalance is supplied, preserve the original behaviour:
        # aligned rows use the ATR value, unaligned rows stay at the configured floor.
        if ce_investment <= 0 and pe_investment <= 0:
            target_pct = atr if ((is_ce and derived_supr == 'BULL') or (is_pe and derived_supr == 'BEAR')) else TGT_PCT_NOT_ALIGNED
            target_pct = max(TGT_PCT_NOT_ALIGNED, min(target_pct, atr))
            calculated_target = entry_prc * (1.0 + (target_pct / 100.0))
            return round(calculated_target, 2)

        # Counter-signal balancing: the max both-side cap is 77%, but only used when a
        # valid imbalance-driven counter signal is active. This keeps the heavy side
        # from carrying too much exposure while the lighter side is kept above the floor.
        total_investment = max(ce_investment + pe_investment, 1.0)
        imbalance_ratio = abs(ce_investment - pe_investment) / total_investment

        def _counter_floor_for(side_name: str) -> float:
            reserve = TGT_PCT_NOT_ALIGNED * (1.0 + imbalance_ratio * 4.0)
            return max(TGT_PCT_NOT_ALIGNED, min(COUNTER_SIGNAL_MAX_BALANCE, reserve))

        target_pct = 0.0
        if is_ce:
            if derived_supr != 'BULL':
                target_pct = TGT_PCT_NOT_ALIGNED
            elif ce_investment >= pe_investment:
                target_pct = TGT_PCT_NOT_ALIGNED
            else:
                target_pct = _counter_floor_for("CE")
        elif is_pe:
            if derived_supr != 'BEAR':
                target_pct = TGT_PCT_NOT_ALIGNED
            elif pe_investment >= ce_investment:
                target_pct = TGT_PCT_NOT_ALIGNED
            else:
                target_pct = _counter_floor_for("PE")

        target_pct = max(TGT_PCT_NOT_ALIGNED, min(target_pct, min(atr, COUNTER_SIGNAL_MAX_BALANCE)))

        # 5️⃣ Final mathematical target premium projection calculation
        calculated_target = entry_prc * (1.0 + (target_pct / 100.0))
        return round(calculated_target, 2)
        
    except Exception as e:
        print(f"{Fore.RED}Error in target_price engine: {e}{Style.RESET_ALL}")
        return 0.0
