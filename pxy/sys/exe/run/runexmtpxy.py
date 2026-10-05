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
    RUNEXMTPXY_TRAILING_DROP_GAP,
)

# ==================== CONFIG (this file's settings) ====================
BRICK_SIZE = RUNEXMTPXY_BRICK_SIZE
INITIAL_LOSS_FLOOR = RUNEXMTPXY_INITIAL_LOSS_FLOOR
PEAK_CEILING = RUNEXMTPXY_PEAK_CEILING
TRAILING_DROP_GAP = RUNEXMTPXY_TRAILING_DROP_GAP
# =======================================================================


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


def compute_stop(current_game_pnl, historical_peak):
    """Returns (winners_peak_brick, active_trailing_exit, is_breached).
    
    UNIFIED STOP (floor & exit are same):
    - Starts at -2000
    - For every point peak grows, stop improves by 2 points (2x multiplier)
    - Formula: stop = -2000 + (peak × 2)
    
    Examples:
    - Peak 0 → stop -2000
    - Peak 100 → stop -1800
    - Peak 1000 → stop 0
    - Peak 2000 → stop 2000 (profit target reached)
    """
    # Negative game P&L must not floor downward into a false negative brick.
    completed_bricks = int(current_game_pnl // BRICK_SIZE) if current_game_pnl >= 0 else 0
    calculated_live_peak = float(completed_bricks * BRICK_SIZE)

    # Peak only moves up within a game
    winners_peak_brick = max(calculated_live_peak, historical_peak)

    # UNIFIED STOP: Both floor and exit threshold
    unified_stop = INITIAL_LOSS_FLOOR + (winners_peak_brick * 2.0)
    
    # PEAK CEILING: Exit when peak reaches 2000
    peak_ceiling_breached = (winners_peak_brick >= PEAK_CEILING)
    
    is_breached = (current_game_pnl <= unified_stop or
                   peak_ceiling_breached)
    return winners_peak_brick, unified_stop, is_breached
