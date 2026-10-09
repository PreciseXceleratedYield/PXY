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
    RUNEXMTPXY_PEAK_MULTIPLIER,
    RUNEXMTPXY_TARGET_PER_ACTIVE_RUNG,
    RUNEXACPXY_CYCLE_TARGET_PCT,
    RUNEXACPXY_STOP_SQUAREOFF_ENABLED,
    RUNEXACPXY_TARGET_SQUAREOFF_ENABLED,
)

# ==================== CONFIG (this file's settings) ====================
BRICK_SIZE = RUNEXMTPXY_BRICK_SIZE
INITIAL_LOSS_FLOOR = RUNEXMTPXY_INITIAL_LOSS_FLOOR
TARGET_PER_ACTIVE_RUNG = RUNEXMTPXY_TARGET_PER_ACTIVE_RUNG
PEAK_CEILING = TARGET_PER_ACTIVE_RUNG * 2
PEAK_MULTIPLIER = RUNEXMTPXY_PEAK_MULTIPLIER
STOP_SQUAREOFF_ENABLED = RUNEXACPXY_STOP_SQUAREOFF_ENABLED
TARGET_SQUAREOFF_ENABLED = RUNEXACPXY_TARGET_SQUAREOFF_ENABLED
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


def cycle_ledger_tags(frame, start_time=None):
    """Return order tags represented by rows at or after a cycle start."""
    df = pd.DataFrame() if frame is None else frame.copy()
    df.columns = [str(column).upper() for column in df.columns]
    if "TAG" not in df.columns:
        return set()
    if start_time is not None and "BUY_TIME" in df.columns:
        timestamps = pd.to_datetime(df["BUY_TIME"], errors="coerce")
        start = pd.Timestamp(start_time)
        df = df.loc[timestamps >= start]
    return {
        str(tag).strip()
        for tag in df["TAG"]
        if str(tag).strip().lower() not in {"", "nan", "none", "null"}
    }


def cycle_start_time(open_df):
    """Return the earliest active lot entry timestamp for a new cycle."""
    df = pd.DataFrame() if open_df is None else open_df.copy()
    df.columns = [str(column).upper() for column in df.columns]
    if "BUY_TIME" not in df.columns or df.empty:
        return None
    timestamps = pd.to_datetime(df["BUY_TIME"], errors="coerce").dropna()
    if timestamps.empty:
        return None
    return min(timestamps).isoformat(sep=" ")


def cycle_risk_metrics(
    open_df,
    closed_df,
    cycle_tags,
    exit_signal,
    target_pct=RUNEXACPXY_CYCLE_TARGET_PCT,
):
    """Measure realized plus unrealized cycle P&L against its premium target."""
    open_positions = pd.DataFrame() if open_df is None else open_df.copy()
    open_positions.columns = [str(column).upper() for column in open_positions.columns]
    closed_positions = pd.DataFrame() if closed_df is None else closed_df.copy()
    closed_positions.columns = [str(column).upper() for column in closed_positions.columns]
    tags = {str(tag).strip() for tag in cycle_tags}

    cycle_rows = []
    for frame in (open_positions, closed_positions):
        if frame.empty or "TAG" not in frame.columns:
            continue
        cycle_rows.append(frame[frame["TAG"].astype(str).str.strip().isin(tags)])
    rows = pd.concat(cycle_rows, ignore_index=True) if cycle_rows else pd.DataFrame()
    if rows.empty:
        cycle_pnl = 0.0
        premium_paid = 0.0
    else:
        quantities = pd.to_numeric(
            rows["QTY"] if "QTY" in rows else pd.Series(0, index=rows.index),
            errors="coerce",
        ).fillna(0).abs()
        buy_prices = pd.to_numeric(
            rows["BUY_PRC"] if "BUY_PRC" in rows else pd.Series(0, index=rows.index),
            errors="coerce",
        ).fillna(0)
        pnl = pd.to_numeric(
            rows["PNL"] if "PNL" in rows else pd.Series(0, index=rows.index),
            errors="coerce",
        ).fillna(0)
        cycle_pnl = float(pnl.sum())
        premium_paid = float((quantities * buy_prices).sum())

    ce_qty = pe_qty = ce_investment = pe_investment = 0.0
    if not open_positions.empty and {"SYMBOL", "QTY", "SELL_PRC"}.issubset(open_positions.columns):
        symbols = open_positions["SYMBOL"].astype(str).str.upper().str.strip()
        quantities = pd.to_numeric(open_positions["QTY"], errors="coerce").fillna(0).clip(lower=0)
        prices = pd.to_numeric(open_positions["SELL_PRC"], errors="coerce").fillna(0).clip(lower=0)
        ce_mask = symbols.str.endswith("CE")
        pe_mask = symbols.str.endswith("PE")
        ce_qty = float(quantities[ce_mask].sum())
        pe_qty = float(quantities[pe_mask].sum())
        ce_investment = float((quantities[ce_mask] * prices[ce_mask]).sum())
        pe_investment = float((quantities[pe_mask] * prices[pe_mask]).sum())

    heavy_side = None
    if ce_investment != pe_investment:
        heavy_side = "CE" if ce_investment > pe_investment else "PE"
    signal = str(exit_signal).upper().strip()
    heavy_side_aligned = (
        (heavy_side == "CE" and signal == "BULL")
        or (heavy_side == "PE" and signal == "BEAR")
    )
    target = premium_paid * float(target_pct) / 100.0
    target_reached = bool(premium_paid > 0 and cycle_pnl >= target and not heavy_side_aligned)
    return {
        "cycle_pnl": cycle_pnl,
        "premium_paid": premium_paid,
        "target": target,
        "ce_qty": ce_qty,
        "pe_qty": pe_qty,
        "ce_investment": ce_investment,
        "pe_investment": pe_investment,
        "heavy_side": heavy_side,
        "heavy_side_aligned": heavy_side_aligned,
        "both_sides_open": ce_qty > 0 and pe_qty > 0,
        "target_reached": target_reached,
    }


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


def target_ceiling(active_count):
    """Scale the portfolio profit target by the number of active open rungs."""
    return TARGET_PER_ACTIVE_RUNG * max(1, int(active_count or 0))


def compute_stop_conditions(current_game_pnl, historical_peak, active_count=2):
    """Return peak, displayed stop line, and independent stop/target breach flags."""
    # Negative game P&L must not floor downward into a false negative brick.
    completed_bricks = int(current_game_pnl // BRICK_SIZE) if current_game_pnl >= 0 else 0
    calculated_live_peak = float(completed_bricks * BRICK_SIZE)

    # Track the peak for the trailing stop.
    winners_peak_brick = max(calculated_live_peak, historical_peak)
    unified_stop = INITIAL_LOSS_FLOOR + (winners_peak_brick * PEAK_MULTIPLIER)
    stop_breached = current_game_pnl <= unified_stop
    target_breached = winners_peak_brick >= target_ceiling(active_count)
    return winners_peak_brick, unified_stop, stop_breached, target_breached
