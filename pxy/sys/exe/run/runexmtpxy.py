#!/usr/bin/env python3
# runexmtpxy.py   (lives in ~/pxy/sys/exe/run/)
#
# MASTER RISK LEDGER, part 3 of 6: the maths only. No file IO, no broker calls.
# Renko trailing stop + hard loss floor on "game P&L". Split out of runexacpxy.py (pure move).
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
)

# ==================== CONFIG (this file's settings) ====================
BRICK_SIZE = RUNEXMTPXY_BRICK_SIZE
INITIAL_LOSS_FLOOR = RUNEXMTPXY_INITIAL_LOSS_FLOOR
PEAK_CEILING = RUNEXMTPXY_PEAK_CEILING
PEAK_MULTIPLIER = RUNEXMTPXY_PEAK_MULTIPLIER
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


def force_zero_ending(val):
    return int(round(val / 10.0) * 10)


def compute_stop(current_game_pnl, historical_peak, active_count=1):
    """Returns (winners_peak_brick, active_trailing_exit, is_breached).

    The fixed loss and profit-target thresholds are divided by the active
    open order-row count. Peak is retained for telemetry only.
    """
    # Negative game P&L must not floor downward into a false negative brick.
    completed_bricks = int(current_game_pnl // BRICK_SIZE) if current_game_pnl >= 0 else 0
    calculated_live_peak = float(completed_bricks * BRICK_SIZE)

    # Peak remains tracked for display, but does not move either exit threshold.
    winners_peak_brick = max(calculated_live_peak, historical_peak)

    threshold_divisor = max(int(active_count), 1)
    loss_exit = INITIAL_LOSS_FLOOR / threshold_divisor
    target_exit = PEAK_CEILING / threshold_divisor
    is_breached = current_game_pnl <= loss_exit or current_game_pnl >= target_exit
    return winners_peak_brick, loss_exit, is_breached
