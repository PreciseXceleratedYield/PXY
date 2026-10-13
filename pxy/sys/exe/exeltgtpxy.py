
import math
import pandas as pd
import re
from colorama import Fore, Style, init
from syscnfgpxy import (
    EXEAMSPXY_MAX_LGT_LOSS,
    EXEAMSPXY_LGT_SCALE,
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


def calculate_lgt(ce_investment, pe_investment, is_ce, index_price, own_count=0):
    """Calculate the capped LGT percentage from investment ratio and lot count."""
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
        own_count_value = float(own_count)
    except (TypeError, ValueError, OverflowError):
        ratio, own_lots = 1.0, 1
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

        lot_count_is_valid = math.isfinite(own_count_value)
        if not ratio_is_valid or not lot_count_is_valid:
            ratio, own_lots = 1.0, 1
        else:
            own_lots = max(1, int(own_count_value))
    magnitude = max(
        EXEAGTPXY_SYSTEM_B_BASE_THRESHOLD,
        round(50.0 * own_lots * ratio, 2),
    )
    return -min(magnitude, EXEAMSPXY_MAX_LGT_LOSS) * EXEAMSPXY_LGT_SCALE


def calculate_tgt(
    is_aligned,
    atr=None,
    side_power=None,
    side_depth=None,
    both_sides_open=False,
    heavy_side=False,
):
    """Return ATR for an aligned heavy side, otherwise the applicable fixed target."""
    if not is_aligned:
        return NOT_ALIGNED_TARGET_PCT
    if both_sides_open and not heavy_side:
        return BOTH_SIDES_ALIGNED_TARGET_PCT

    try:
        atr_value, power_value, depth_value = (
            float(atr),
            float(side_power),
            float(side_depth),
        )
    except (TypeError, ValueError):
        raise ValueError("Aligned target requires ATR, side power, and side depth.")
    if (
        not all(math.isfinite(value) for value in (atr_value, power_value, depth_value))
        or atr_value <= 0
        or power_value <= 0
        or depth_value <= 0
    ):
        raise ValueError("Aligned target inputs must be finite positive values.")
    return max(atr_value + (NOT_ALIGNED_TARGET_PCT * depth_value), atr_value * power_value)


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
    """Calculate the target from exit alignment and the open side counts.

    Args:
        row: dict containing entry, symbol, exit, and ATR target inputs.
        ce_investment/pe_investment: accepted for call compatibility.
        ce_count/pe_count: open call and put counts.
    
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
        
        # Calculate the positive target price.
        calculated_target = entry_prc * (1.0 + (target_pct / 100.0))
        return round(calculated_target, 2)
        
    except Exception as e:
        print(f"{Fore.RED}Error in target_price engine: {e}{Style.RESET_ALL}")
        return 0.0
