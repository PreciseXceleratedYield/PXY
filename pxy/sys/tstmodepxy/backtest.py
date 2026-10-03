"""One-session NIFTY candle replay using production signals and safe proxies."""

import argparse
import csv
import os
import sys
from datetime import datetime, time
from pathlib import Path

import pandas as pd
import yfinance as yf

SYS_DIR = Path(__file__).resolve().parent.parent
if str(SYS_DIR) not in sys.path:
    sys.path.insert(0, str(SYS_DIR))

from .pointbacktest import (
    FORCE_EXIT_TIME,
    MARKET_CLOSE,
    MARKET_OPEN,
    is_actual_market_hours,
    simulate_point_session,
)
from syscnfgpxy import (
    EXEENTRPXY_ENTRY_CUTOFF,
    EXEENTRPXY_PREOPEN_END,
    EXEENTRPXY_PREOPEN_START,
    EXEENTRPXY_SQUAREOFF_END,
    EXEEXITPXY_SQOFF_ALL_START,
    RUNNIFTYPXY_HOLIDAYS,
    SYSCNFGPXY_TICKER,
    SYSCNFGPXY_TIMEZONE,
    SYSDTAFPXY_DEFAULT_TARGET_ROWS,
)
from sysdtafpxy import transform_market_data

DATA_SESSION_OPEN = time(9, 15)


def fetch_recent_index_history():
    """Fetch recent 1-minute history; extra sessions provide indicator warmup."""
    frame = yf.Ticker(SYSCNFGPXY_TICKER).history(
        period="7d",
        interval="1m",
        auto_adjust=False,
        actions=False,
    )
    if frame is None or frame.empty:
        raise RuntimeError(
            f"Yahoo Finance returned no 1-minute history for {SYSCNFGPXY_TICKER}."
        )

    if isinstance(frame.columns, pd.MultiIndex):
        frame.columns = frame.columns.get_level_values(0)
    missing = {"Open", "High", "Low", "Close"} - set(frame.columns)
    if missing:
        raise RuntimeError(f"Historical data is missing columns: {sorted(missing)}")

    if not isinstance(frame.index, pd.DatetimeIndex):
        frame.index = pd.to_datetime(frame.index)
    if frame.index.tz is None:
        frame.index = frame.index.tz_localize(SYSCNFGPXY_TIMEZONE)
    else:
        frame.index = frame.index.tz_convert(SYSCNFGPXY_TIMEZONE)

    frame = frame[["Open", "High", "Low", "Close"]].dropna().sort_index()
    local_index = frame.index.tz_localize(None)
    session_times = local_index.time
    frame = frame[
        (session_times >= DATA_SESSION_OPEN)
        & (session_times <= MARKET_CLOSE)
        & (frame.index.weekday < 5)
    ]
    if frame.empty:
        raise RuntimeError("Yahoo Finance returned no weekday market-session candles.")
    return frame


def latest_completed_session(history, required_final_time=FORCE_EXIT_TIME):
    """Select the newest session with data through the configured square-off time."""
    available_sessions = []
    for session_date, frame in history.groupby(history.index.date):
        if frame.index[-1].time().replace(tzinfo=None) >= required_final_time:
            available_sessions.append(session_date)
    if not available_sessions:
        raise RuntimeError(
            "No completed NIFTY session found in Yahoo's recent 1-minute history."
        )
    return max(available_sessions)


def calculate_strategy_signals(history, session_date):
    """Evaluate production transformation and entry/exit signal code bar by bar."""
    from sysentrpxy import get_entry_signal
    import sysmktpxy

    sysmktpxy.DEBUG = False
    records = []
    target_indexes = [
        index for index, timestamp in enumerate(history.index)
        if timestamp.date() == session_date
        and timestamp.time().replace(tzinfo=None) >= MARKET_OPEN
        and timestamp.time().replace(tzinfo=None) <= MARKET_CLOSE
    ]
    for index in target_indexes:
        available = history.iloc[: index + 1]
        current_day = available.index[-1].date()
        intraday_history = available[available.index.date == current_day]
        if len(intraday_history) >= SYSDTAFPXY_DEFAULT_TARGET_ROWS + 5:
            available = intraday_history
        strategy_history = transform_market_data(available)
        strategy_history = strategy_history.tail(SYSDTAFPXY_DEFAULT_TARGET_ROWS)
        entry, exit_signal = get_entry_signal(strategy_history)
        next_timestamp = None
        next_open = None
        if index + 1 < len(history) and history.index[index + 1].date() == session_date:
            next_timestamp = history.index[index + 1]
            next_open = float(history["Open"].iloc[index + 1])
        records.append(
            {
                "timestamp": strategy_history.index[-1],
                "spot": float(history["Close"].iloc[index]),
                "entry": entry,
                "exit": exit_signal,
                "next_timestamp": next_timestamp,
                "next_open": next_open,
            }
        )
    if not records:
        raise RuntimeError(f"No replay bars found for completed session {session_date}.")
    return records


def write_csv(path, rows, fieldnames):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    try:
        with temporary.open("w", newline="", encoding="utf-8") as output:
            writer = csv.DictWriter(output, fieldnames=fieldnames)
            writer.writeheader()
            for row in rows:
                writer.writerow(
                    {
                        key: value.isoformat() if hasattr(value, "isoformat") else value
                        for key, value in row.items()
                    }
                )
        os.replace(temporary, path)
    except OSError:
        if temporary.exists():
            temporary.unlink()
        raise


def write_session_csvs(output_dir, session_date, trades, decisions):
    run_stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    prefix = f"nifty-point-replay-{session_date}-{run_stamp}"
    trade_path = output_dir / f"{prefix}-trades.csv"
    decision_path = output_dir / f"{prefix}-bars.csv"
    trade_fields = (
        "side", "entry_time", "exit_time", "entry_spot", "exit_spot",
        "points", "exit_reason",
    )
    decision_fields = (
        "timestamp", "spot", "entry_signal", "exit_signal",
        "position_before", "action", "position_after", "realized_points",
        "next_bar_timestamp", "next_bar_open",
    )
    write_csv(trade_path, trades, trade_fields)
    write_csv(decision_path, decisions, decision_fields)
    return trade_path, decision_path


def print_report(history, session_date, trades, decisions, trade_path, decision_path):
    points = [trade["points"] for trade in trades]
    total_points = sum(points)
    winners = sum(value > 0 for value in points)
    losers = sum(value < 0 for value in points)
    hit_rate = 100 * winners / len(trades) if trades else 0.0

    print("=" * 72)
    print("PXY ONE-SESSION NIFTY POINT-PROXY REPLAY")
    print("=" * 72)
    print(f"Instrument: {SYSCNFGPXY_TICKER} | Session: {session_date}")
    print(
        f"Source: Yahoo Finance 1-minute candles | Replayed bars: {len(decisions)} | "
        f"Loaded history bars: {len(history)}"
    )
    print(
        "Production entry/signal code and entry gates are replayed. Simulated "
        "orders fill at the following candle open using CE/PE spot-point proxies."
    )
    print(
        "Not represented: option-premium target exits, broker/OMS behavior, "
        "averaging/counter orders, costs, or slippage."
    )
    print(
        f"Entries start at {MARKET_OPEN:%H:%M} IST; simulated square-off begins "
        f"at {EXEEXITPXY_SQOFF_ALL_START:%H:%M} IST."
    )
    print("-" * 72)
    print(
        f"Trades: {len(trades)} | Wins: {winners} | Losses: {losers} | "
        f"Hit rate: {hit_rate:.1f}%"
    )
    print(f"Net directional index points (one virtual unit): {total_points:+.2f}")
    print(f"CSV trade ledger: {trade_path}")
    print(f"CSV bar-by-bar decisions: {decision_path}")
    print("=" * 72)


def run_backtest(output_dir=None):
    if is_actual_market_hours(holidays=RUNNIFTYPXY_HOLIDAYS):
        raise RuntimeError(
            "Walk-forward replay is disabled during weekday market hours "
            "(09:15-15:30 IST)."
        )
    history = fetch_recent_index_history()
    holiday_dates = set(RUNNIFTYPXY_HOLIDAYS)
    history = history[
        ~history.index.strftime("%d-%b-%Y").isin(holiday_dates)
    ]
    session_date = latest_completed_session(
        history, required_final_time=MARKET_CLOSE
    )
    bars = calculate_strategy_signals(history, session_date)
    trades, decisions = simulate_point_session(
        bars,
        preopen_start=EXEENTRPXY_PREOPEN_START,
        preopen_end=EXEENTRPXY_PREOPEN_END,
        entry_cutoff=EXEENTRPXY_ENTRY_CUTOFF,
        squareoff_end=EXEENTRPXY_SQUAREOFF_END,
        force_exit_time=EXEEXITPXY_SQOFF_ALL_START,
    )
    output_dir = output_dir or Path.home() / "pxy-backtest-results"
    trade_path, decision_path = write_session_csvs(
        Path(output_dir), session_date, trades, decisions
    )
    print_report(history, session_date, trades, decisions, trade_path, decision_path)
    return trades, decisions


def main(argv=None):
    parser = argparse.ArgumentParser(
        description=(
            "Replay the latest completed NIFTY 1-minute session using production "
            "signals and simulated index-point fills; no broker orders are sent."
        )
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path.home() / "pxy-backtest-results",
        help="Directory for CSV ledgers (default: ~/pxy-backtest-results).",
    )
    args = parser.parse_args(argv)
    try:
        run_backtest(args.output_dir)
    except (RuntimeError, ValueError, OSError) as error:
        print(f"BACKTEST ERROR: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
