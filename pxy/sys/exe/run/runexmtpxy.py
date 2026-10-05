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
    RUNEXMTPXY_PEAK_GAP_FLOOR_PCT,
    RUNEXMTPXY_TIGHTEN_PER_EXTRA_ROW,
    RUNEXMTPXY_TRAILING_DROP_GAP,
)

# ==================== CONFIG (this file's settings) ====================
BRICK_SIZE = RUNEXMTPXY_BRICK_SIZE
INITIAL_LOSS_FLOOR = RUNEXMTPXY_INITIAL_LOSS_FLOOR
PEAK_CEILING = RUNEXMTPXY_PEAK_CEILING
TRAILING_DROP_GAP = RUNEXMTPXY_TRAILING_DROP_GAP
PEAK_GAP_FLOOR_PCT = RUNEXMTPXY_PEAK_GAP_FLOOR_PCT
TIGHTEN_PER_EXTRA_ROW = RUNEXMTPXY_TIGHTEN_PER_EXTRA_ROW
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


def compute_stop(current_game_pnl, historical_peak, open_rows):
    """Returns (winners_peak_brick, active_trailing_exit, is_breached).
    
    DYNAMIC LOSS FLOOR:
    - Base floor: -2000
    - For every 50 points of peak growth, relax floor by 100
    - Formula: dynamic_floor = -2000 + (peak / 50 × 100) = -2000 + (peak × 2)
    - Example: Peak 200 → Floor = -2000 + 400 = -1600 (more forgiving as you profit)
    """
    # Negative game P&L must not floor downward into a false negative brick.
    completed_bricks = int(current_game_pnl // BRICK_SIZE) if current_game_pnl >= 0 else 0
    calculated_live_peak = float(completed_bricks * BRICK_SIZE)

    # Peak only moves up within a game
    winners_peak_brick = max(calculated_live_peak, historical_peak)

    # DYNAMIC LOSS FLOOR: As peak grows, allow deeper losses (more forgiving)
    # Peak grows by 50 (1 brick) → Floor relaxes by 100 (2x multiplier)
    # Peak 0 → Floor -2000
    # Peak 200 → Floor -2000 + (200×2) = -1600
    # Peak 500 → Floor -2000 + (500×2) = -1000
    dynamic_loss_floor = INITIAL_LOSS_FLOOR + (winners_peak_brick * 2.0)

    # Stop = peak - gap. The gap starts at TRAILING_DROP_GAP and shrinks per banked brick by
    # BRICK_SIZE x (open rows - 1): 1 row -> no shrink, 2 rows -> 50 per brick, 3 rows -> 100 ...
    # The shrink is floored at PEAK_GAP_FLOOR_PCT of the peak.
    stop_climb_multiplier = max(1, open_rows)
    bricks_banked = winners_peak_brick / BRICK_SIZE if BRICK_SIZE > 0 else 0.0
    shrink_per_brick = BRICK_SIZE * (stop_climb_multiplier - 1)
    shrinking_gap = TRAILING_DROP_GAP - (bricks_banked * shrink_per_brick)
    peak_floor_gap = winners_peak_brick * PEAK_GAP_FLOOR_PCT
    base_gap = min(TRAILING_DROP_GAP, max(peak_floor_gap, shrinking_gap))

    # Every extra open row tightens the gap a further 5%; when rows drop, the gap widens back out.
    extra_rows = max(0, open_rows - 1)
    drop_gap = base_gap * (1.0 - extra_rows * TIGHTEN_PER_EXTRA_ROW)
    drop_gap = min(base_gap, max(peak_floor_gap, drop_gap))

    active_trailing_exit = winners_peak_brick - drop_gap
    
    # PEAK CEILING: Exit when peak reaches configured ceiling (default 1000, changeable to 2000 etc)
    peak_ceiling_breached = (winners_peak_brick >= PEAK_CEILING)
    
    is_breached = (current_game_pnl <= dynamic_loss_floor or
                   current_game_pnl <= active_trailing_exit or
                   peak_ceiling_breached)
    return winners_peak_brick, active_trailing_exit, is_breached
