#!/usr/bin/env python3
# runexmtpxy.py   (lives in ~/pxy/sys/exe/run/)
#
# MASTER RISK LEDGER, part 3 of 6: the maths only. No file IO, no broker calls.
# Renko trailing stop + hard loss floor on "game P&L". Split out of runexacpxy.py (pure move).
import math
import sys
from pathlib import Path

import pandas as pd

SYS_DIR = Path(__file__).resolve().parents[2]
if str(SYS_DIR) not in sys.path:
    sys.path.insert(0, str(SYS_DIR))

from syscnfgpxy import (
    RUNEXMTPXY_BRICK_SIZE,
    RUNEXMTPXY_INITIAL_LOSS_FLOOR,
    RUNEXMTPXY_PEAK_CEILING,
    RUNEXMTPXY_PEAK_MULTIPLIER,
    RUNEXACPXY_STOP_SQUAREOFF_ENABLED,
    RUNEXACPXY_TARGET_SQUAREOFF_ENABLED,
)

# ==================== CONFIG (this file's settings) ====================
BRICK_SIZE = RUNEXMTPXY_BRICK_SIZE
INITIAL_LOSS_FLOOR = RUNEXMTPXY_INITIAL_LOSS_FLOOR
PEAK_CEILING = RUNEXMTPXY_PEAK_CEILING
PEAK_MULTIPLIER = RUNEXMTPXY_PEAK_MULTIPLIER
STOP_SQUAREOFF_ENABLED = RUNEXACPXY_STOP_SQUAREOFF_ENABLED
TARGET_SQUAREOFF_ENABLED = RUNEXACPXY_TARGET_SQUAREOFF_ENABLED
# =======================================================================


def midday_risk_activation_due(control_enabled, activated, current_time, activation_time):
    """Check whether enabled risk control reached its configured activation time."""
    return bool(
        control_enabled
        and not activated
        and activation_time is not None
        and current_time >= activation_time
    )


def _prep_frame(df):
    """Handle None, upper-case headers, pad missing columns, force numeric."""
    df = pd.DataFrame() if df is None else df.copy()
    df.columns = [str(c).upper() for c in df.columns]
    for col in ("BUY_PRC", "SELL_PRC", "PNL"):
        if col not in df.columns:
            df[col] = 0.0
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
    return df


def _both_empty(open_df, closed_df):
    return ((open_df is None or open_df.empty) and
            (closed_df is None or closed_df.empty))


def compute_totals(open_df, closed_df):
    df_open = _prep_frame(open_df)
    df_closed = _prep_frame(closed_df)

    win_open = df_open[df_open["BUY_PRC"] < df_open["SELL_PRC"]]
    win_closed = df_closed[df_closed["BUY_PRC"] < df_closed["SELL_PRC"]]
    total = float(df_open["PNL"].sum() + df_closed["PNL"].sum())
    winners = float(win_open["PNL"].sum() + win_closed["PNL"].sum())
    return {
        "total": total,
        "winners": winners,
        "losers": total - winners,
        "open_rows": len(df_open),
    }


def large_invested_side_aligned(open_df, direction):
    """Return whether the higher-invested option side matches market direction."""
    df = pd.DataFrame() if open_df is None else open_df.copy()
    df.columns = [str(column).upper() for column in df.columns]
    if not {"SYMBOL", "QTY", "SELL_PRC"}.issubset(df.columns):
        return False

    symbols = df["SYMBOL"].astype(str).str.upper().str.strip()
    quantities = pd.to_numeric(df["QTY"], errors="coerce").fillna(0.0)
    prices = pd.to_numeric(df["SELL_PRC"], errors="coerce").fillna(0.0)
    investments = quantities * prices
    ce_investment = float(investments[symbols.str.endswith("CE")].sum())
    pe_investment = float(investments[symbols.str.endswith("PE")].sum())
    if (
        not math.isfinite(ce_investment)
        or not math.isfinite(pe_investment)
        or max(ce_investment, pe_investment) <= 0
        or ce_investment == pe_investment
    ):
        return False

    signal = str(direction).upper().strip()
    return (
        ce_investment > pe_investment and signal == "UP"
    ) or (
        pe_investment > ce_investment and signal == "DOWN"
    )


def force_zero_ending(val):
    return int(round(val / 10.0) * 10)


def compute_stop(current_game_pnl, historical_peak):
    """Return peak, displayed PEAK stop line, and whether an enabled exit hit."""
    winners_peak_brick, stop_line, stop_breached, target_breached = (
        compute_stop_conditions(current_game_pnl, historical_peak)
    )
    return (
        winners_peak_brick,
        stop_line,
        risk_squareoff_due(stop_breached, target_breached),
    )


def risk_squareoff_due(stop_breached, target_breached):
    """Return whether either enabled risk threshold should square off."""
    return bool(
        (STOP_SQUAREOFF_ENABLED and stop_breached)
        or (TARGET_SQUAREOFF_ENABLED and target_breached)
    )


def compute_stop_conditions(current_game_pnl, historical_peak):
    """Return peak, displayed stop line, and independent stop/target breach flags."""
    # Negative game P&L must not floor downward into a false negative brick.
    completed_bricks = int(current_game_pnl // BRICK_SIZE) if current_game_pnl >= 0 else 0
    calculated_live_peak = float(completed_bricks * BRICK_SIZE)

    # Track the peak for the trailing stop.
    winners_peak_brick = max(calculated_live_peak, historical_peak)
    unified_stop = INITIAL_LOSS_FLOOR + (winners_peak_brick * PEAK_MULTIPLIER)
    stop_breached = current_game_pnl <= unified_stop
    target_breached = winners_peak_brick >= PEAK_CEILING
    return winners_peak_brick, unified_stop, stop_breached, target_breached
