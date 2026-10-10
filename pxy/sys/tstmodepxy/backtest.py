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
from .replay_adapter import ProductionPipeReplay, SIM_PERCENT_SCALE
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


def scale_sim_lgt_calculator(calculator):
    """Scale a production percentage-based averaging threshold for spot SIM."""
    def calculate(*args, **kwargs):
        return calculator(*args, **kwargs) / SIM_PERCENT_SCALE

    return calculate


def calculate_heikin_ashi(history):
    """Return standard Heikin-Ashi OHLC candles for an OHLC history frame."""
    required = {"Open", "High", "Low", "Close"}
    missing = required - set(history.columns)
    if missing:
        raise ValueError(f"Heikin-Ashi input is missing columns: {sorted(missing)}")
    if history.empty:
        return history.loc[:, ["Open", "High", "Low", "Close"]].copy()

    source = history.loc[:, ["Open", "High", "Low", "Close"]].astype(float)
    ha_close = source[["Open", "High", "Low", "Close"]].mean(axis=1)
    ha_open = pd.Series(index=source.index, dtype=float)
    ha_open.iloc[0] = (source["Open"].iloc[0] + source["Close"].iloc[0]) / 2.0
    for index in range(1, len(source)):
        ha_open.iloc[index] = (
            ha_open.iloc[index - 1] + ha_close.iloc[index - 1]
        ) / 2.0

    return pd.DataFrame(
        {
            "Open": ha_open,
            "High": pd.concat([source["High"], ha_open, ha_close], axis=1).max(axis=1),
            "Low": pd.concat([source["Low"], ha_open, ha_close], axis=1).min(axis=1),
            "Close": ha_close,
        },
        index=source.index,
    )


def heikin_ashi_entry_exit_signals(ha_history):
    """Emit entries on HA color switches and exits from the current HA state."""
    entries = []
    exits = []
    previous_state = "NONE"
    for ha_open, ha_close in zip(ha_history["Open"], ha_history["Close"]):
        if ha_close > ha_open:
            state = "BULL"
        elif ha_close < ha_open:
            state = "BEAR"
        else:
            state = previous_state

        if state == "BULL" and previous_state != "BULL":
            entry = "BUY"
        elif state == "BEAR" and previous_state != "BEAR":
            entry = "SELL"
        else:
            entry = "NONE"
        entries.append(entry)
        exits.append(state)
        previous_state = state
    return entries, exits


def calculate_strategy_signals(
    history, session_date, record_limit=None, heikin_ashi=False
):
    """Build production snapshots for ALL candles of a full trading session."""
    sys.path.insert(0, str(SYS_DIR / "exe"))
    dashboard = importlib.import_module("sysdashpxy")
    signal_history = calculate_heikin_ashi(history) if heikin_ashi else history
    if heikin_ashi:
        ha_entries, ha_exits = heikin_ashi_entry_exit_signals(signal_history)
    else:
        ha_entries = ha_exits = None
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
        available = signal_history.iloc[: index + 1]
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
        entry_signal = snapshot.get("entry", "NONE")
        exit_signal = snapshot.get("exit", "NONE")
        if heikin_ashi:
            entry_signal = ha_entries[index]
            exit_signal = ha_exits[index]
            snapshot["entry"] = entry_signal
            snapshot["exit"] = exit_signal
        records.append(
            {
                "timestamp": history.index[index],
                "spot": float(history["Close"].iloc[index]),
                "entry": entry_signal,
                "exit": exit_signal,
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


def _book_reason(trade, entry_orders, entry_decision, exit_log):
    entry_log = entry_decision.get("pipe_output", "") if entry_decision else ""
    entry_signal = entry_decision.get("entry_signal", "NONE") if entry_decision else "NONE"
    exit_signal = entry_decision.get("exit_signal", "NONE") if entry_decision else "NONE"
    entry_text = entry_log.lower()
    if "fresh entry" in entry_text:
        entry_reason = f"Fresh-entry {entry_signal} signal was accepted while flat."
    elif "counter-buy" in entry_text:
        entry_reason = f"Counter-leg triggered by {exit_signal} exit signal."
    elif "averaged" in entry_text or "averaging" in entry_text:
        entry_reason = "Averaging loss threshold and placement gates passed."
    elif any(
        str(order.get("GuiOrdId", "")).startswith("CB")
        for order in entry_orders
    ):
        entry_reason = f"Counter-leg triggered by {exit_signal} exit signal."
    else:
        entry_reason = f"Production entry pipe accepted {entry_signal}."

    exit_time = datetime.fromisoformat(trade["exit_time"])
    if trade["exit_reason"] == "risk_bar" or "SIM CYCLE POINT TARGET EXIT" in exit_log:
        exit_reason = "Cycle-risk target was reached and its confirmation gate passed."
    elif exit_time.time() >= EXEEXITPXY_SQOFF_START:
        exit_reason = "Scheduled square-off closed the remaining position."
    elif "Target Hit & PnL Met" in exit_log:
        exit_reason = "Production target and minimum-P&L gates both passed."
    elif "Deep reversal:" in exit_log:
        exit_reason = "Deep-reversal signal and scaled loss gate triggered the exit."
    else:
        exit_reason = f"Production exit pipe closed the position on exit state {exit_signal}."
    return f"{entry_reason} {exit_reason}"


def print_book_table(book_number, book_legs):
    actions = []
    reasons = []
    total_points = 0.0
    for trade, entry_orders, entry_decision, exit_log in book_legs:
        entry_time = datetime.fromisoformat(trade["entry_time"]).strftime("%H:%M")
        exit_time = datetime.fromisoformat(trade["exit_time"]).strftime("%H:%M")
        points = float(trade["index_points_per_unit"]) * int(trade["quantity"])
        total_points += points
        actions.append(
            f"BUY {trade['side']} @ {entry_time} "
            f"({float(trade['entry_spot']):.2f}) → SELL @ {exit_time} "
            f"({float(trade['exit_spot']):.2f}); {points:+.2f} pts"
        )
        reasons.append(_book_reason(trade, entry_orders, entry_decision, exit_log))
    action = (
        f"Book {book_number}: " + "; ".join(actions)
        + f"; Total: {total_points:+.2f} pts"
    )
    why = " ".join(dict.fromkeys(reasons))
    print("| Action | Why action |")
    print("|---|---|")
    print(f"| {action} | {why} |", flush=True)


class SimBookCycle:
    """Collect completed SIM legs until the whole simulated portfolio is flat."""

    def __init__(self):
        self.is_open = False
        self.legs = []

    def record_tick(self, position_before, position_after, new_legs, has_new_entry):
        flat = "0CE0PE"
        if not self.is_open and (
            position_before != flat
            or position_after != flat
            or new_legs
            or has_new_entry
        ):
            self.is_open = True
        if self.is_open:
            self.legs.extend(new_legs)
        if self.is_open and position_after == flat:
            completed = self.legs
            self.is_open = False
            self.legs = []
            return completed
        return None


def print_report(
    history, session_dates, trades, decisions, trade_path, decision_path,
    orders_path, runtime_log, incomplete_positions=(), heikin_ashi=False,
):
    total_points = sum(trade["points"] for trade in trades)
    production_exits = sum(
        trade["exit_reason"] == "production_exit" for trade in trades
    )
    risk_bar_exits = sum(trade["exit_reason"] == "risk_bar" for trade in trades)
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
        "pipe code runs against a simulated broker, including the cycle risk target."
    )
    print(
        "Signal source: Heikin-Ashi color switches and current candle state."
        if heikin_ashi
        else "Signal source: production entry and exit logic."
    )
    print(
        "SIM fills, target checks, cycle risk, and P&L all use index spot prices. "
        "Production target, averaging, cycle-risk, and deep-reversal percentages "
        "are divided by 200; each simulated lot is "
        "one unit for index-point results. "
        "CE gains when spot rises; PE gains when spot falls."
    )
    print(
        f"Entries start at {MARKET_OPEN:%H:%M} IST; staged square-off starts "
        f"at {EXEEXITPXY_SQOFF_START:%H:%M} IST and all-leg square-off at "
        f"{EXEEXITPXY_SQOFF_ALL_START:%H:%M} IST."
    )
    print("-" * 72)
    print(
        f"Closed lots: {len(trades)} | Production exits: {production_exits} | "
        f"Risk-bar exits: {risk_bar_exits} | "
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
    session_date=None,
    heikin_ashi=False,
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
    if session_date is None:
        session_dates = recent_sessions_with_records(
            history, min(session_count, len(available_dates) - 1)
        )
    else:
        if session_date not in available_dates:
            raise ValueError(
                f"Selected session {session_date} is not an available completed "
                "trading session."
            )
        session_dates = [session_date]
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
            history, session_date, record_limit, heikin_ashi=heikin_ashi
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
            "Cycle risk target is enabled.\n"
        )
    selected_lgt = lgt_calculator or production_lgt
    all_trades = []
    all_simulated_orders = []
    incomplete_positions = []
    decisions = []
    interactive_books = sys.stdin.isatty()
    stopped_early = False
    book_number = 0
    for session_date in session_dates:
        broker = SimulatedBroker()
        book_cycle = SimBookCycle()
        with tempfile.TemporaryDirectory(prefix="pxy-walk-forward-") as temporary_state:
            with ProductionPipeReplay(
                SYS_DIR,
                broker,
                Path(temporary_state),
                risk_bar_enabled=True,
            ) as engine:
                engine.avg_controller.calculate_lgt = scale_sim_lgt_calculator(
                    selected_lgt
                )
                for bar in bars_by_session[session_date]:
                    before = broker.position_summary()
                    first_new_order = len(broker.orders)
                    open_trade_count = len(broker.trades())
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
                    newly_closed_trades = broker.trades()[open_trade_count:]
                    after = broker.position_summary()
                    new_book_legs = []
                    for trade in newly_closed_trades:
                        trade_tag = trade["tag"]
                        entry_orders = [
                            order for order in broker.orders
                            if order["GuiOrdId"] == trade_tag
                            and order["trnsTp"] == "B"
                        ]
                        entry_decision = next(
                            (
                                decision for decision in reversed(decisions)
                                if decision["timestamp"].strftime("%Y-%m-%d %H:%M:%S")
                                == trade["entry_time"]
                            ),
                            None,
                        )
                        if entry_decision is None:
                            entry_decision = {
                                "entry_signal": bar["entry"],
                                "exit_signal": bar["exit"],
                                "pipe_output": pipe_output,
                            }
                        new_book_legs.append(
                            (
                                trade,
                                entry_orders,
                                entry_decision,
                                f"{bar['snapshot_log']}{pipe_output}",
                            )
                        )
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
                    completed_book = book_cycle.record_tick(
                        before,
                        after,
                        new_book_legs,
                        any(
                            order["trnsTp"] == "B"
                            for order in current_orders
                        ),
                    )
                    if completed_book is not None:
                        if completed_book:
                            book_number += 1
                            print_book_table(book_number, completed_book)
                            if interactive_books:
                                try:
                                    command = input().strip().lower()
                                except (EOFError, KeyboardInterrupt):
                                    command = "q"
                                if command == "q":
                                    stopped_early = True
                    if stopped_early:
                        break
            remaining = broker.position_summary()
            if remaining != "0CE0PE" and record_limit is None and not stopped_early:
                raise RuntimeError(
                    f"Scheduled square-off did not flatten simulated positions "
                    f"for {session_date}: {remaining}."
                )
            if remaining != "0CE0PE":
                incomplete_positions.append(f"{session_date}: {remaining}")
        all_simulated_orders.extend(broker.orders)
        for trade in broker.trades():
            exit_clock = datetime.fromisoformat(trade["exit_time"]).time()
            exit_reason = trade["exit_reason"]
            if (
                exit_reason != "risk_bar"
                and exit_clock >= EXEEXITPXY_SQOFF_START
            ):
                exit_reason = "scheduled_squareoff"
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
        if stopped_early:
            break

    if all_simulated_orders:
        write_csv(
            orders_path,
            all_simulated_orders,
            tuple(all_simulated_orders[0].keys()),
        )
    trade_path, decision_path = write_session_csvs(
        output_dir, session_label, all_trades, decisions
    )
    if not interactive_books:
        print_report(
            history, session_dates, all_trades, decisions, trade_path, decision_path,
            orders_path, runtime_log, incomplete_positions, heikin_ashi=heikin_ashi,
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
        "--session-date",
        type=lambda value: datetime.strptime(value, "%Y-%m-%d").date(),
        default=None,
        help="Replay one exact completed trading session (YYYY-MM-DD).",
    )
    parser.add_argument(
        "--heikin-ashi",
        action="store_true",
        help=(
            "Use HA bullish/bearish switches for BUY/SELL entries and the "
            "current HA state for BULL/BEAR exits."
        ),
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
            session_date=args.session_date,
            heikin_ashi=args.heikin_ashi,
        )
    except (RuntimeError, ValueError, OSError) as error:
        print(f"SIM ERROR: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
