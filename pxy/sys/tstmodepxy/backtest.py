"""One-session NIFTY candle replay using production signals and safe proxies."""

import argparse
import csv
from contextlib import redirect_stdout
import importlib
import io
import os
import sys
import tempfile
from datetime import datetime, time, timedelta
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import yfinance as yf

SYS_DIR = Path(__file__).resolve().parent.parent
if str(SYS_DIR) not in sys.path:
    sys.path.insert(0, str(SYS_DIR))

from .pointbacktest import (
    MARKET_CLOSE,
    MARKET_OPEN,
)
from .broker_sim import SimulatedBroker
from .replay_adapter import ProductionPipeReplay
from syscnfgpxy import (
    EXEEXITPXY_SQOFF_ALL_START,
    RUNMODE,
    RUNNIFTYPXY_HOLIDAYS,
    SYSCNFGPXY_TICKER,
    SYSCNFGPXY_TIMEZONE,
    SYSDTAFPXY_DEFAULT_TARGET_ROWS,
)
from sysdtafpxy import transform_market_data

DATA_SESSION_OPEN = time(9, 15)
OHLC_COLUMNS = {"Open", "High", "Low", "Close"}
MAX_INTRADAY_LOOKBACK_DAYS = 7


def _normalize_history_columns(frame):
    """Flatten Yahoo columns using the level that actually contains OHLC names."""
    if not isinstance(frame.columns, pd.MultiIndex):
        return frame

    levels = [
        [str(column) for column in frame.columns.get_level_values(level)]
        for level in range(frame.columns.nlevels)
    ]
    selected = max(
        levels,
        key=lambda columns: len(OHLC_COLUMNS.intersection(columns)),
    )
    frame = frame.copy()
    frame.columns = selected
    return frame.loc[:, ~frame.columns.duplicated(keep="first")]


def _prepare_index_history(frame):
    if frame is None or frame.empty:
        return pd.DataFrame(columns=["Open", "High", "Low", "Close"])
    frame = _normalize_history_columns(frame)
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
    return frame


def _has_completed_session(history):
    if history is None or history.empty:
        return False
    return any(
        session.index[-1].time().replace(tzinfo=None) >= MARKET_CLOSE
        for _, session in history.groupby(history.index.date)
    )


def _today_ist():
    return pd.Timestamp.now(tz=SYSCNFGPXY_TIMEZONE).date()


def fetch_recent_index_history():
    """Fetch warmup history, walking back by day until a complete session is found."""
    ticker = yf.Ticker(SYSCNFGPXY_TICKER)
    failures = []
    try:
        frame = _prepare_index_history(
            ticker.history(
                period=f"{MAX_INTRADAY_LOOKBACK_DAYS}d",
                interval="1m",
                auto_adjust=False,
                actions=False,
            )
        )
    except Exception as error:
        frame = pd.DataFrame(columns=["Open", "High", "Low", "Close"])
        failures.append(f"recent-history request: {error}")

    if _has_completed_session(frame):
        return frame

    searched_dates = []
    today = _today_ist()
    holidays = set(RUNNIFTYPXY_HOLIDAYS)
    for day_offset in range(MAX_INTRADAY_LOOKBACK_DAYS):
        session_day = today - timedelta(days=day_offset)
        if session_day.weekday() >= 5 or session_day.strftime("%d-%b-%Y") in holidays:
            continue
        searched_dates.append(session_day.isoformat())
        try:
            daily = _prepare_index_history(
                ticker.history(
                    start=session_day.isoformat(),
                    end=(session_day + timedelta(days=1)).isoformat(),
                    interval="1m",
                    auto_adjust=False,
                    actions=False,
                )
            )
        except Exception as error:
            failures.append(f"{session_day.isoformat()}: {error}")
            continue

        if not daily.empty:
            frame = pd.concat([frame, daily]).sort_index()
            frame = frame.loc[~frame.index.duplicated(keep="last")]
        if _has_completed_session(frame):
            return frame

    detail = f" Searched dates: {', '.join(searched_dates) or 'none'}."
    if failures:
        detail += f" Request errors: {'; '.join(failures)}"
    raise RuntimeError(
        f"Could not find a completed 1-minute NIFTY session within Yahoo's "
        f"{MAX_INTRADAY_LOOKBACK_DAYS}-day intraday-history window.{detail}"
    )


def latest_session_with_records(history, record_limit=100):
    """Select a random trading session with enough candles for a replay."""
    import random
    available_sessions = []
    for session_date, frame in history.groupby(history.index.date):
        session_bars = frame[
            (frame.index.time >= MARKET_OPEN)
            & (frame.index.time <= MARKET_CLOSE)
        ]
        if len(session_bars) >= record_limit:
            available_sessions.append(session_date)
    if not available_sessions:
        raise RuntimeError(
            f"No recent NIFTY session contains {record_limit} replay candles."
        )
    return random.choice(available_sessions)


def calculate_strategy_signals(history, session_date, record_limit=100):
    """Build production snapshots for the first N candles of a session."""
    sys.path.insert(0, str(SYS_DIR / "exe"))
    dashboard = importlib.import_module("sysdashpxy")
    records = []
    target_indexes = [
        index for index, timestamp in enumerate(history.index)
        if timestamp.date() == session_date
        and timestamp.time().replace(tzinfo=None) >= MARKET_OPEN
        and timestamp.time().replace(tzinfo=None) <= MARKET_CLOSE
    ][:record_limit]
    for index in target_indexes:
        available = history.iloc[: index + 1]
        transformed = transform_market_data(available).tail(
            SYSDTAFPXY_DEFAULT_TARGET_ROWS
        )
        transformed.attrs["data_fallback"] = False
        output = io.StringIO()
        with patch.object(dashboard, "fetch_yf_data", return_value=transformed):
            with redirect_stdout(output):
                snapshot = dashboard.get_full_snapshot()
        if not snapshot:
            raise RuntimeError(
                f"Production dashboard returned no snapshot at {history.index[index]}."
            )
        records.append(
            {
                "timestamp": history.index[index],
                "spot": float(history["Close"].iloc[index]),
                "entry": snapshot.get("entry", "NONE"),
                "exit": snapshot.get("exit", "NONE"),
                "snapshot": snapshot,
                "snapshot_log": output.getvalue(),
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
    prefix = f"nifty-sim-replay-{session_date}-{run_stamp}"
    trade_path = output_dir / f"{prefix}-trades.csv"
    decision_path = output_dir / f"{prefix}-bars.csv"
    trade_fields = (
        "side", "entry_time", "exit_time", "entry_spot", "exit_spot",
        "points", "exit_reason", "quantity", "simulated_option_entry",
        "simulated_option_exit",
    )
    decision_fields = (
        "timestamp", "execution_timestamp", "spot", "execution_spot",
        "entry_signal", "exit_signal", "position_before", "position_after",
        "orders_created", "order_tags", "pipe_output",
    )
    write_csv(trade_path, trades, trade_fields)
    write_csv(decision_path, decisions, decision_fields)
    return trade_path, decision_path


def print_report(
    history, session_date, trades, decisions, trade_path, decision_path,
    orders_path, runtime_log,
):
    points = [trade["points"] for trade in trades]
    total_points = sum(points)
    winners = sum(value > 0 for value in points)
    losers = sum(value < 0 for value in points)
    hit_rate = 100 * winners / len(trades) if trades else 0.0

    print("=" * 72)
    print("PXY SIM PRODUCTION-CYCLE REPLAY")
    print("=" * 72)
    print(f"Instrument: {SYSCNFGPXY_TICKER} | Session: {session_date}")
    print(
        f"Source: Yahoo Finance 1-minute candles | Data records/cycles: "
        f"{len(decisions)} | Warmup history bars: {len(history)}"
    )
    print(
        "Production dashboard, exit, entry, averaging, counter-leg, and square-off "
        "pipe code runs against a simulated broker with a CSV order ledger. Orders are filled "
        "at each candle close using CE/PE spot-point/premium proxies."
    )
    print(
        "Option premiums are synthetic directional proxies, not historical option "
        "quotes. Results are not real option P&L; costs and slippage are excluded."
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
    print(f"CSV simulated broker orders: {orders_path}")
    print(f"Production pipe runtime log: {runtime_log}")
    print("=" * 72)


def run_backtest(output_dir=None, record_limit=100):
    if RUNMODE != "SIM":
        raise RuntimeError(
            f"Walk-forward replay requires RUNMODE='SIM'; current RUNMODE={RUNMODE!r}."
        )
    if record_limit <= 0:
        raise ValueError("record_limit must be a positive integer.")
    history = fetch_recent_index_history()
    holiday_dates = set(RUNNIFTYPXY_HOLIDAYS)
    history = history[
        ~history.index.strftime("%d-%b-%Y").isin(holiday_dates)
    ]
    session_date = latest_session_with_records(history, record_limit)
    bars = calculate_strategy_signals(history, session_date, record_limit)
    output_dir = output_dir or Path.home() / "pxy-sim-results"
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    runtime_log = output_dir / (
        f"nifty-pipe-replay-{session_date}-{datetime.now():%Y%m%d-%H%M%S}.log"
    )
    orders_path = output_dir / (
        f"nifty-sim-replay-{session_date}-{datetime.now():%Y%m%d-%H%M%S}-orders.csv"
    )
    with runtime_log.open("w", encoding="utf-8") as stream:
        stream.write(
            "Production pipe output for simulated replay. "
            "No live broker session or external order process is permitted.\n"
        )
    broker = SimulatedBroker(orders_csv=orders_path)
    decisions = []
    with tempfile.TemporaryDirectory(prefix="pxy-walk-forward-") as temporary_state:
        with ProductionPipeReplay(SYS_DIR, broker, Path(temporary_state)) as engine:
            for bar in bars:
                before = broker.position_summary()
                first_new_order = len(broker.orders)
                if bar["snapshot_log"]:
                    with runtime_log.open("a", encoding="utf-8") as stream:
                        stream.write(
                            f"\n===== PRODUCTION DASHBOARD {bar['timestamp']} =====\n"
                            f"{bar['snapshot_log']}"
                        )
                pipe_output = engine.run_tick(
                    bar["snapshot"],
                    bar["timestamp"],
                    bar["spot"],
                    runtime_log,
                )
                current_orders = broker.orders[first_new_order:]
                after = broker.position_summary()
                decisions.append(
                    {
                        "timestamp": bar["timestamp"],
                        "execution_timestamp": bar["timestamp"],
                        "spot": bar["spot"],
                        "execution_spot": bar["spot"],
                        "entry_signal": bar["entry"],
                        "exit_signal": bar["exit"],
                        "position_before": before,
                        "position_after": after,
                        "orders_created": len(current_orders),
                        "order_tags": "|".join(
                            order["GuiOrdId"] for order in current_orders
                        ),
                        "pipe_output": f"{bar['snapshot_log']}{pipe_output}",
                    }
                )
    trades = [
        {
            "side": trade["side"],
            "entry_time": trade["entry_time"],
            "exit_time": trade["exit_time"],
            "entry_spot": trade["entry_spot"],
            "exit_spot": trade["exit_spot"],
            "points": trade["index_points_per_unit"],
            "exit_reason": trade["exit_reason"],
            "quantity": trade["quantity"],
            "simulated_option_entry": trade["simulated_option_entry"],
            "simulated_option_exit": trade["simulated_option_exit"],
        }
        for trade in broker.trades()
    ]
    trade_path, decision_path = write_session_csvs(
        output_dir, session_date, trades, decisions
    )
    print_report(
        history, session_date, trades, decisions, trade_path, decision_path,
        orders_path, runtime_log,
    )
    return trades, decisions


def main(argv=None):
    parser = argparse.ArgumentParser(
        description=(
            "Replay the first N candles from the latest eligible NIFTY 1-minute "
            "session through production pipes and a CSV-backed simulated broker."
        )
    )
    parser.add_argument(
        "--records",
        type=int,
        default=100,
        help="Number of consecutive Yahoo candles and production cycles (default: 100).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path.home() / "pxy-sim-results",
        help="Directory for CSV ledgers (default: ~/pxy-sim-results).",
    )
    args = parser.parse_args(argv)
    try:
        run_backtest(args.output_dir, record_limit=args.records)
    except (RuntimeError, ValueError, OSError) as error:
        print(f"SIM ERROR: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
