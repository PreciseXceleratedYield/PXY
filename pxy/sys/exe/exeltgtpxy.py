#!/usr/bin/env python3
import sys
from pathlib import Path
from datetime import datetime, time as dt_time

# ----------------- PATH FIX (MUST BE AT ABSOLUTE TOP) -----------------
HERE = Path(__file__).resolve().parent
SYS_DIR = HERE.parent
PXY_DIR = SYS_DIR.parent

# Prioritize SYS_DIR so Python finds all sys*.py files first
for path in (SYS_DIR, PXY_DIR, HERE):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

# ----------------- IMPORTS -----------------
import math
import pandas as pd
import re
from colorama import Fore, Style, init

from syscnfgpxy import (
    EXETGTPXY_EXIT_KEY_COLUMN,
    EXETGTPXY_PRD_BASE_FACTOR,
    EXETGTPXY_PRD_BOTH_SIDES_BASE_PCT,
    EXETGTPXY_PRD_LATE_DAY_TIME,
    EXETGTPXY_PRD_MAX_TARGET_PCT,
    SYSCNFGPXY_TIMEZONE,
    X,
)

# ==================== CONFIG ====================
EXIT_KEY_COLUMN = EXETGTPXY_EXIT_KEY_COLUMN
# ================================================

init(autoreset=True)

_warned = set()


def _warn_once(key, msg):
    """Print a warning only the first time it occurs in this process."""
    if key not in _warned:
        _warned.add(key)
        print(f"{Fore.YELLOW}⚠️ {msg}{Style.RESET_ALL}")


# === SURGICAL CHANGE START (Error Fallbacks Added) ===
def calculate_lgt(is_aligned, ce_count=0, pe_count=0, is_ce=True, ce_investment=0.0, pe_investment=0.0, ce_pnl_pct=0.0, pe_pnl_pct=0.0, ce_capital=None, pe_capital=None):
    """LGT = -14 * OwnCapital / OppositeWorth."""
    try:
        own_capital = float((ce_capital if is_ce else pe_capital) if (ce_capital if is_ce else pe_capital) is not None else (ce_investment if is_ce else pe_investment))
        opposite_worth = float(pe_investment if is_ce else ce_investment)
        if not all(math.isfinite(v) for v in (own_capital, opposite_worth)):
            raise ValueError("non-finite LGT worth")
        if own_capital <= 0 or opposite_worth <= 0:
            return -14.0
        raw_lgt = -14.0 * (own_capital / opposite_worth)
        return max(-99.0, min(0.0, raw_lgt))
    except (TypeError, ValueError, OverflowError, ZeroDivisionError) as e:
        _warn_once("lgt_err", f"Error in calculate_lgt: {e}. Falling back to -14.0.")
        return -14.0


def calculate_tgt(
    is_aligned,
    atr=None,
    side_power=None,
    side_depth=None,
    both_sides_open=False,
    heavy_side=False,
    target_time=None,
    exit_signal=None,
    opposite_count=0,
    own_count=0,
    own_worth=0.0,
    opposite_worth=0.0,
    tsma_state=None,
    is_ce=None,
):
    """Calculate targets using shared X for single-side and dual-side rules."""
    try:
        current_time = target_time

        if current_time is None:
            current_time = datetime.now(SYSCNFGPXY_TIMEZONE)

        if hasattr(current_time, "time"):
            current_time = current_time.time()

        # Both-side targets: aligned uses the worth ratio; unaligned uses X / 10.
        if both_sides_open:
            if not is_aligned:
                return X / 10.0
            try:
                own = float(own_worth)
                opposite = float(opposite_worth)
                if not (math.isfinite(own) and math.isfinite(opposite)) or own <= 0 or opposite <= 0:
                    return 0.0
                return X * (opposite / own)
            except (TypeError, ValueError, OverflowError, ZeroDivisionError):
                return 0.0

        # From the configured late-day cutoff (15:14 IST), set 99% target for every position,
        # regardless of alignment or whether one or both sides are open.
        if current_time >= EXETGTPXY_PRD_LATE_DAY_TIME:
            return EXETGTPXY_PRD_MAX_TARGET_PCT

        def positive_factor(value):
            try:
                parsed = float(value)
            except (TypeError, ValueError, OverflowError):
                return 1.0

            return (
                parsed
                if math.isfinite(parsed) and parsed > 0
                else 1.0
            )

        own_depth = positive_factor(side_depth)
        own_power = positive_factor(side_power)

        # With only one active option side, use the higher of own power and own depth
        # from 09:15 until 15:14. The late-day override remains authoritative.
        if not both_sides_open and dt_time(9, 15) <= current_time < EXETGTPXY_PRD_LATE_DAY_TIME:
            target_pct = (
                X / max(own_power, own_depth)
                if is_aligned
                else X / 10.0
            )
            return min(EXETGTPXY_PRD_MAX_TARGET_PCT, target_pct)

        if not is_aligned:
            # Both-side non-aligned target is fixed at 1.4%.
            return 1.4

        # When both CE and PE are open, aligned positions use the 99% target.
        if both_sides_open:
            return EXETGTPXY_PRD_MAX_TARGET_PCT

        # Preserve the existing aligned fallback for other cases.
        both_sides_base = EXETGTPXY_PRD_BOTH_SIDES_BASE_PCT
        target_pct = (
            both_sides_base
            + (both_sides_base / max(own_power, own_depth))
        )

        return min(EXETGTPXY_PRD_MAX_TARGET_PCT, target_pct)

    except Exception as e:
        _warn_once(
            "tgt_err",
            f"Error in calculate_tgt: {e}. Falling back to 25.0",
        )
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
    """Calculate CE and PE current market exposure from sell prices."""
    if df is None or df.empty:
        return 0.0, 0.0

    symbols = df['symbol'].astype(str).str.upper()
    qtys = pd.to_numeric(
        df['qty'], errors='coerce'
    ).fillna(0).clip(lower=0)

    sell_prices = pd.to_numeric(
        df['sell_prc'], errors='coerce'
    ).fillna(0).clip(lower=0)

    invested = qtys * sell_prices

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
            _warn_once(
                "exit",
                f"unrecognised exit value '{exit_signal}' "
                f"(expected BULL/BEAR/SIDE/NONE).",
            )

        is_ce = symbol.endswith('CE')
        is_pe = symbol.endswith('PE')

        if not is_ce and not is_pe:
            return round(entry_prc, 2)

        is_aligned = (
            exit_signal in ("NONE", "SIDE")
            or (exit_signal == "BULL" and is_ce)
            or (exit_signal == "BEAR" and is_pe)
        )

        target_pct = calculate_tgt(
            is_aligned,
            atr=row.get("atr"),
            side_power=row.get(
                "ce_power" if is_ce else "pe_power"
            ),
            side_depth=row.get(
                "hkin_ce_depth" if is_ce else "hkin_pe_depth"
            ),
            both_sides_open=(ce_count > 0 and pe_count > 0),
            heavy_side=(
                ce_investment > pe_investment
                if is_ce
                else pe_investment > ce_investment
            ),
            target_time=target_time,
            exit_signal=exit_signal,
            opposite_count=pe_count if is_ce else ce_count,
            own_count=ce_count if is_ce else pe_count,
            own_worth=ce_investment if is_ce else pe_investment,
            opposite_worth=pe_investment if is_ce else ce_investment,
            tsma_state=row.get("tsma"),
            is_ce=is_ce,
        )

        calculated_target = entry_prc * (
            1.0 + (target_pct / 100.0)
        )

        return round(calculated_target, 2)

    except Exception as e:
        print(
            f"{Fore.RED}Error in target_price engine: "
            f"{e}{Style.RESET_ALL}"
        )
        return 0.0
