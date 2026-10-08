"""Multi-session NIFTY replay using production pipes and spot-point scoring."""

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
EXE_DIR = SYS_DIR / "exe"
if str(EXE_DIR) not in sys.path:
    sys.path.insert(0, str(EXE_DIR))

from exeltgtpxy import calculate_lgt as production_lgt

from .pointbacktest import (
    MARKET_CLOSE,
    MARKET_OPEN,
)
from .broker_sim import SimulatedBroker
from .replay_adapter import ProductionPipeReplay
from syscnfgpxy import (
    EXEEXITPXY_SQOFF_ALL_START,
    EXEEXITPXY_SQOFF_START,
    SYSMODEPXY_RUN_MODE as RUNMODE,
    RUNNIFTYPXY_HOLIDAYS,
    SYSCNFGPXY_TICKER,
    SYSCNFGPXY_TIMEZONE,
    SYSDTAFPXY_DEFAULT_TARGET_ROWS,
    TSTPOINTBTPXY_TRADING_DAY_START,
)
from sysdtafpxy import transform_market_data

DATA_SESSION_OPEN = TSTPOINTBTPXY_TRADING_DAY_START
OHLC_COLUMNS = {"Open", "High", "Low", "Close"}
MAX_INTRADAY_LOOKBACK_DAYS = 28
DEFAULT_SESSION_COUNT = 7


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


def _today_ist():
    return pd.Timestamp.now(tz=SYSCNFGPXY_TIMEZONE).date()


def _completed_session_dates(history):
    if history is None or history.empty:
        return []
    completed = []
    for session_date, session in history.groupby(history.index.date):
        market_bars = session[
            (session.index.time >= MARKET_OPEN)
            & (session.index.time <= MARKET_CLOSE)
        ]
        if (
            not market_bars.empty
            and market_bars.index[-1].time().replace(tzinfo=None) >= MARKET_CLOSE
        ):
            completed.append(session_date)
    return sorted(completed)


def fetch_recent_index_history(session_count=DEFAULT_SESSION_COUNT):
    """Fetch enough one-minute history for N complete sessions plus warm-up."""
    if session_count < 1:
        raise ValueError("session_count must be a positive integer.")
    ticker = yf.Ticker(SYSCNFGPXY_TICKER)
    failures = []
    try:
        frame = _prepare_index_history(
            ticker.history(
                period="7d",
                interval="1m",
                auto_adjust=False,
                actions=False,
            )
        )
    except Exception as error:
        frame = pd.DataFrame(columns=["Open", "High", "Low", "Close"])
        failures.append(f"recent-history request: {error}")

    searched_dates = []
    today = _today_ist()
    holidays = set(RUNNIFTYPXY_HOLIDAYS)
    required_sessions = session_count + 1
    for day_offset in range(MAX_INTRADAY_LOOKBACK_DAYS):
        complete_dates = [
            session_date
            for session_date in _completed_session_dates(frame)
            if session_date.strftime("%d-%b-%Y") not in holidays
        ]
        if len(complete_dates) >= required_sessions:
            break
        session_day = today - timedelta(days=day_offset)
        if (
            session_day.weekday() >= 5
            or session_day.strftime("%d-%b-%Y") in holidays
            or session_day in complete_dates
        ):
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

    completed = _completed_session_dates(frame)
    if completed:
        return frame

    detail = f" Searched dates: {', '.join(searched_dates) or 'none'}."
    if failures:
        detail += f" Request errors: {'; '.join(failures)}"
    raise RuntimeError(
        f"Could not find any completed 1-minute NIFTY session within Yahoo's "
        f"{MAX_INTRADAY_LOOKBACK_DAYS}-day intraday-history window.{detail}"
    )


def latest_session_with_records(history, record_limit=None):
    """Select the latest completed session for callers that need one day."""
    available_sessions = _completed_session_dates(history)
    if not available_sessions:
        raise RuntimeError(
            "No completed recent NIFTY session found for full-day replay."
        )
    return max(available_sessions)


def recent_sessions_with_records(history, session_count=DEFAULT_SESSION_COUNT):
    """Select up to N latest completed sessions, oldest first."""
    if session_count < 1:
        raise ValueError("session_count must be a positive integer.")
    available_sessions = _completed_session_dates(history)
    if not available_sessions:
        raise RuntimeError("No completed recent NIFTY sessions found for replay.")
    return available_sessions[-session_count:]


def score_spot_points(side, entry_spot, exit_spot, quantity):
    """Return signed spot points multiplied by filled quantity."""
    side = str(side).upper().strip()
    if side not in {"CE", "PE"}:
        raise ValueError("side must be CE or PE.")
    direction = 1.0 if side == "CE" else -1.0
    return (float(exit_spot) - float(entry_spot)) * direction * int(quantity)


def calculate_strategy_signals(history, session_date, record_limit=None):
    """Build production snapshots for ALL candles of a full trading session."""
    sys.path.insert(0, str(SYS_DIR / "exe"))
    dashboard = importlib.import_module("sysdashpxy")
    records = []
    target_indexes = [
        index for index, timestamp in enumerate(history.index)
        if timestamp.date() == session_date
        and timestamp.time().replace(tzinfo=None) >= MARKET_OPEN
        and timestamp.time().replace(tzinfo=None) <= MARKET_CLOSE
    ]
    # Use all candles if record_limit is None
    if record_limit is not None:
        target_indexes = target_indexes[:record_limit]
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
        "session", "side", "entry_time", "exit_time", "entry_spot", "exit_spot",
        "spot_points_per_unit", "quantity", "points", "exit_reason",
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
    history, session_dates, trades, decisions, trade_path, decision_path,
    orders_path, runtime_log, incomplete_positions=(),
):
    total_points = sum(trade["points"] for trade in trades)
    target_exits = sum(trade["exit_reason"] == "target_exit" for trade in trades)
    squareoff_exits = sum(
        trade["exit_reason"] == "scheduled_squareoff" for trade in trades
    )

    print("=" * 72)
    print("PXY SIM PRODUCTION-CYCLE REPLAY")
    print("=" * 72)
    session_label = (
        str(session_dates[0])
        if len(session_dates) == 1
        else f"{session_dates[0]} through {session_dates[-1]}"
    )
    print(f"Instrument: {SYSCNFGPXY_TICKER} | Sessions: {session_label}")
    print(
        f"Source: Yahoo Finance 1-minute candles | Data records/cycles: "
        f"{len(decisions)} | Warmup history bars: {len(history)}"
    )
    print(
        "Production dashboard, exit, entry, averaging, counter-leg, and square-off "
        "pipe code runs against a simulated broker. Portfolio risk-bar exits are "
        "disabled; remaining positions are expected to close at scheduled square-off."
    )
    print(
        "Score is signed NIFTY spot movement × filled quantity (CE gains on UP; "
        "PE gains on DOWN). Synthetic spot-linked premiums are used only to exercise "
        "the unchanged premium-target trigger; they are not used in the score."
    )
    print(
        f"Entries start at {MARKET_OPEN:%H:%M} IST; staged square-off starts "
        f"at {EXEEXITPXY_SQOFF_START:%H:%M} IST and all-leg square-off at "
        f"{EXEEXITPXY_SQOFF_ALL_START:%H:%M} IST."
    )
    print("-" * 72)
    print(
        f"Closed lots: {len(trades)} | Target exits: {target_exits} | "
        f"Scheduled square-off exits: {squareoff_exits}"
    )
    print(f"Quantity-weighted spot points: {total_points:+.2f}")
    if incomplete_positions:
        print(
            "Diagnostic replay ended before square-off; open positions excluded "
            f"from the score: {incomplete_positions}"
        )
    print(f"CSV trade ledger: {trade_path}")
    print(f"CSV bar-by-bar decisions: {decision_path}")
    print(f"CSV simulated broker orders: {orders_path}")
    print(f"Production pipe runtime log: {runtime_log}")
    print("=" * 72)


def run_backtest(
    output_dir=None,
    record_limit=None,
    session_count=DEFAULT_SESSION_COUNT,
    lgt_calculator=None,
):
    if RUNMODE != "SIM":
        raise RuntimeError(
            f"Walk-forward replay requires RUNMODE='SIM'; current RUNMODE={RUNMODE!r}."
        )
    if record_limit is not None and record_limit <= 0:
        raise ValueError("record_limit must be a positive integer or None for all candles.")
    if session_count <= 0:
        raise ValueError("session_count must be a positive integer.")
    history = fetch_recent_index_history(session_count)
    holiday_dates = set(RUNNIFTYPXY_HOLIDAYS)
    history = history[
        ~history.index.strftime("%d-%b-%Y").isin(holiday_dates)
    ]
    available_dates = _completed_session_dates(history)
    if len(available_dates) < 2:
        raise RuntimeError(
            "At least two completed one-minute sessions are required: one "
            "for indicator warm-up and one for replay."
        )
    session_dates = recent_sessions_with_records(
        history, min(session_count, len(available_dates) - 1)
    )
    first_session = session_dates[0]
    warmup_dates = _completed_session_dates(history)
    warmup_date = max(
        (day for day in warmup_dates if day < first_session),
        default=None,
    )
    if warmup_date is None:
        raise RuntimeError(
            "No completed one-minute session is available before the first "
            "selected session for indicator warm-up."
        )
    bars_by_session = {
        session_date: calculate_strategy_signals(
            history, session_date, record_limit
        )
        for session_date in session_dates
    }
    output_dir = output_dir or Path.home() / "pxy-sim-results"
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    session_label = f"{session_dates[0]}-{session_dates[-1]}"
    runtime_log = output_dir / (
        f"nifty-pipe-replay-{session_label}-{datetime.now():%Y%m%d-%H%M%S}.log"
    )
    orders_path = output_dir / (
        f"nifty-sim-replay-{session_label}-{datetime.now():%Y%m%d-%H%M%S}-orders.csv"
    )
    with runtime_log.open("w", encoding="utf-8") as stream:
        stream.write(
            "Production pipe output for simulated replay. "
            "No live broker session or external order process is permitted. "
            "Portfolio risk bar is disabled.\n"
        )
    selected_lgt = lgt_calculator or production_lgt
    all_trades = []
    all_simulated_orders = []
    incomplete_positions = []
    decisions = []
    for session_date in session_dates:
        broker = SimulatedBroker()
        with tempfile.TemporaryDirectory(prefix="pxy-walk-forward-") as temporary_state:
            with ProductionPipeReplay(
                SYS_DIR,
                broker,
                Path(temporary_state),
                risk_bar_enabled=False,
            ) as engine:
                engine.avg_controller.calculate_lgt = selected_lgt
                for bar in bars_by_session[session_date]:
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
            remaining = broker.position_summary()
            if remaining != "0CE0PE" and record_limit is None:
                raise RuntimeError(
                    f"Scheduled square-off did not flatten simulated positions "
                    f"for {session_date}: {remaining}."
                )
            if remaining != "0CE0PE":
                incomplete_positions.append(f"{session_date}: {remaining}")
        all_simulated_orders.extend(broker.orders)
        for trade in broker.trades():
            exit_clock = datetime.fromisoformat(trade["exit_time"]).time()
            exit_reason = (
                "scheduled_squareoff"
                if exit_clock >= EXEEXITPXY_SQOFF_START
                else "target_exit"
            )
            points_per_unit = score_spot_points(
                trade["side"],
                trade["entry_spot"],
                trade["exit_spot"],
                1,
            )
            all_trades.append(
                {
                    "session": str(session_date),
                    "side": trade["side"],
                    "entry_time": trade["entry_time"],
                    "exit_time": trade["exit_time"],
                    "entry_spot": trade["entry_spot"],
                    "exit_spot": trade["exit_spot"],
                    "spot_points_per_unit": points_per_unit,
                    "quantity": trade["quantity"],
                    "points": points_per_unit * trade["quantity"],
                    "exit_reason": exit_reason,
                }
            )

    if all_simulated_orders:
        write_csv(
            orders_path,
            all_simulated_orders,
            tuple(all_simulated_orders[0].keys()),
        )
    trade_path, decision_path = write_session_csvs(
        output_dir, session_label, all_trades, decisions
    )
    print_report(
        history, session_dates, all_trades, decisions, trade_path, decision_path,
        orders_path, runtime_log, incomplete_positions,
    )
    return all_trades, decisions


def main(argv=None):
    parser = argparse.ArgumentParser(
        description=(
            "Replay ALL candles from the latest eligible NIFTY 1-minute "
            "session through production pipes and a CSV-backed simulated broker."
        )
    )
    parser.add_argument(
        "--records",
        type=int,
        default=None,
        help="Number of consecutive Yahoo candles and production cycles (default: None = all candles).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path.home() / "pxy-sim-results",
        help="Directory for CSV ledgers (default: ~/pxy-sim-results).",
    )
    parser.add_argument(
        "--sessions",
        type=int,
        default=None,
        help=f"Latest completed 1-minute sessions to replay (default: {DEFAULT_SESSION_COUNT}; "
        "one session by default when --records is specified).",
    )
    parser.add_argument(
        "--lgt-constant",
        type=float,
        default=None,
        help="Manually test a constant loss threshold percentage, e.g. 8 for -8%%.",
    )
    args = parser.parse_args(argv)
    try:
        if args.lgt_constant is not None and not 0 < args.lgt_constant <= 77:
            raise ValueError("--lgt-constant must be greater than 0 and at most 77.")
        lgt_calculator = (
            None
            if args.lgt_constant is None
            else lambda _ce, _pe, is_ce: -args.lgt_constant
        )
        run_backtest(
            args.output_dir,
            record_limit=args.records,
            session_count=(
                args.sessions
                if args.sessions is not None
                else (1 if args.records is not None else DEFAULT_SESSION_COUNT)
            ),
            lgt_calculator=lgt_calculator,
        )
    except (RuntimeError, ValueError, OSError) as error:
        print(f"SIM ERROR: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
