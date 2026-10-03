"""One-session NIFTY candle replay using production signals and safe proxies."""

import argparse
import csv
import importlib
import io
import os
import sys
import tempfile
from contextlib import ExitStack, redirect_stderr, redirect_stdout
from datetime import datetime, time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

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
)
from .broker_sim import SimulatedBroker
from syscnfgpxy import (
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
    """Run the production dashboard snapshot over each historical close."""
    sys.path.insert(0, str(SYS_DIR / "exe"))
    dashboard = importlib.import_module("sysdashpxy")
    records = []
    target_indexes = [
        index for index, timestamp in enumerate(history.index)
        if timestamp.date() == session_date
        and timestamp.time().replace(tzinfo=None) >= DATA_SESSION_OPEN
        and timestamp.time().replace(tzinfo=None) <= MARKET_CLOSE
    ]
    for index in target_indexes:
        available = history.iloc[: index + 1]
        current_day = available.index[-1].date()
        intraday_history = available[available.index.date == current_day]
        if len(intraday_history) >= SYSDTAFPXY_DEFAULT_TARGET_ROWS + 5:
            available = intraday_history
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
        next_timestamp = None
        next_open = None
        if index + 1 < len(history) and history.index[index + 1].date() == session_date:
            next_timestamp = history.index[index + 1]
            next_open = float(history["Open"].iloc[index + 1])
        records.append(
            {
                "timestamp": history.index[index],
                "spot": float(history["Close"].iloc[index]),
                "entry": snapshot.get("entry", "NONE"),
                "exit": snapshot.get("exit", "NONE"),
                "snapshot": snapshot,
                "snapshot_log": output.getvalue(),
                "next_timestamp": next_timestamp,
                "next_open": next_open,
            }
        )
    if not records:
        raise RuntimeError(f"No replay bars found for completed session {session_date}.")
    return records


def run_production_pipes(snapshot, timestamp, spot, broker, state_dir, runtime_log):
    """Execute the real production exit, entry, then averaging pipe functions.

    All dependencies with external effects are bound to an in-memory broker,
    injected historical snapshot, or temporary runtime state.
    """
    exe_dir = SYS_DIR / "exe"
    run_dir = exe_dir / "run"
    for path in (exe_dir, run_dir):
        if str(path) not in sys.path:
            sys.path.insert(0, str(path))

    exists = os.path.exists
    squareoff_log = (SYS_DIR.parent / "web" / "websqrpxy.json").resolve()

    def exists_without_production_squareoff_state(path):
        try:
            if Path(path).resolve() == squareoff_log:
                return False
        except (TypeError, OSError):
            pass
        return exists(path)

    with patch("os.path.exists", exists_without_production_squareoff_state):
        entry_pipe = importlib.import_module("exeentrpxy")
        exit_pipe = importlib.import_module("exeexitpxy")
        avg_pipe = importlib.import_module("exeavgpxy")
        oms = importlib.import_module("exeomspxy")
        lilo = importlib.import_module("runlilopxy")
    avg_controller = importlib.import_module("exeavxpxy")
    averaging_orders = importlib.import_module("exeamspxy")
    counter_pipe = importlib.import_module("execbuypxy")
    squareoff_pipe = importlib.import_module("exesqrpxy")
    dynamic_entry = importlib.import_module("exedynpxy")

    class ReplayClock(datetime):
        @classmethod
        def now(cls, tz=None):
            current = (
                timestamp.to_pydatetime()
                if hasattr(timestamp, "to_pydatetime")
                else timestamp
            )
            if tz is None:
                return current.replace(tzinfo=None)
            if current.tzinfo is None:
                return current.replace(tzinfo=tz)
            return current.astimezone(tz)

    def simulated_shell(command):
        name = Path(str(command).strip().split()[0]).name
        if name == "pxybuyce":
            broker.place_order(
                trading_symbol="NIFTY-WF-CE",
                transaction_type="B",
                quantity=broker.quantity,
                tag=broker.next_tag("WF"),
            )
        elif name == "pxybuype":
            broker.place_order(
                trading_symbol="NIFTY-WF-PE",
                transaction_type="B",
                quantity=broker.quantity,
                tag=broker.next_tag("WF"),
            )
        else:
            raise RuntimeError(f"Unexpected production shell command blocked: {command}")
        return 0

    def simulated_popen(command, *args, **kwargs):
        command_path = Path(command[0]).name if isinstance(command, (list, tuple)) else ""
        if command_path == "pxybuyce":
            broker.place_order(
                trading_symbol="NIFTY-WF-CE",
                transaction_type="B",
                quantity=broker.quantity,
                tag=broker.next_tag("CB"),
            )
        elif command_path == "pxybuype":
            broker.place_order(
                trading_symbol="NIFTY-WF-PE",
                transaction_type="B",
                quantity=broker.quantity,
                tag=broker.next_tag("CB"),
            )
        elif isinstance(command, (list, tuple)) and any(
            Path(str(part)).name == "sysddmppxy.py" for part in command
        ):
            pass
        else:
            raise RuntimeError(f"Unexpected production process launch blocked: {command}")
        return SimpleNamespace(pid=0, returncode=0)

    def simulated_squareoff(command, *args, **kwargs):
        if not isinstance(command, (list, tuple)) or not any(
            str(part).endswith("exesqrpxy.py") for part in command
        ):
            raise RuntimeError(f"Unexpected production subprocess blocked: {command}")
        all_args = [
            str(part) for part in command[1:]
            if not str(part).endswith("exesqrpxy.py")
        ]
        with patch.object(squareoff_pipe, "get_session", return_value=broker), \
             patch.object(squareoff_pipe, "get_combined_data", oms.get_combined_data), \
             patch.object(squareoff_pipe, "datetime", ReplayClock), \
             patch.object(squareoff_pipe, "subprocess") as squareoff_subprocess, \
             patch.object(squareoff_pipe.sys, "argv", ["exesqrpxy.py", *all_args]):
            squareoff_subprocess.Popen.return_value = SimpleNamespace(pid=0)
            squareoff_pipe.exit_all_positions()
        return SimpleNamespace(returncode=0)

    output = io.StringIO()

    def real_get_all_data():
        return snapshot

    def production_dispatch(_name, provider, *args, **kwargs):
        kwargs.pop("test_kwargs", None)
        return provider(*args, **kwargs)

    broker.set_market(timestamp, spot)
    state_dir.mkdir(parents=True, exist_ok=True)
    temporary_daily_purge = SimpleNamespace(
        daily_purge_check=lambda: None,
        execute_master_risk_ledger=lambda *args, **kwargs: None,
    )
    patchers = [
        patch.object(entry_pipe, "get_all_data", real_get_all_data),
        patch.object(entry_pipe, "get_session", return_value=broker),
        patch.object(
            entry_pipe,
            "get_position_summary",
            lambda _client: broker.position_summary(),
        ),
        patch.object(entry_pipe, "dispatch_mode", production_dispatch),
        patch.object(entry_pipe.os, "system", simulated_shell),
        patch.object(entry_pipe, "datetime", ReplayClock),
        patch.object(exit_pipe, "get_combined_data", oms.get_combined_data),
        patch.object(exit_pipe, "get_session", return_value=broker),
        patch.object(exit_pipe, "dispatch_mode", production_dispatch),
        patch.object(exit_pipe, "ledger_busy", return_value=False),
        patch.object(exit_pipe, "datetime", ReplayClock),
        patch.object(exit_pipe, "_load_locks", return_value={}),
        patch.object(exit_pipe, "_mark_lock", lambda _key: None),
        patch.object(exit_pipe, "process_metrics_print_and_dump", lambda *args: None),
        patch.object(exit_pipe, "dump_idle_json", lambda *args: None),
        patch.object(avg_pipe, "get_combined_data", oms.get_combined_data),
        patch.object(avg_pipe, "get_session", return_value=broker),
        patch.object(avg_pipe, "dispatch_mode", production_dispatch),
        patch.object(avg_pipe, "dump_idle_json", lambda *args: None),
        patch.object(oms, "dispatch_mode", production_dispatch),
        patch.object(oms.syspxy, "get_all_data", real_get_all_data),
        patch.object(oms, "print_market_dashboard", lambda _market_df: None),
        patch.object(oms, "get_session", return_value=broker),
        patch.object(lilo, "dispatch_mode", production_dispatch),
        patch.object(lilo, "dump_to_json", lambda _df: None),
        patch.object(lilo, "dump_livpos_to_json", lambda _rows: None),
        patch.object(avg_controller, "datetime", ReplayClock),
        patch.object(avg_controller, "ledger_busy", return_value=False),
        patch.object(
            avg_controller,
            "get_position_summary",
            lambda _client: broker.position_summary(),
        ),
        patch.object(
            avg_controller,
            "WEB_AVG_JSON_REL",
            str(state_dir / "webavgpxy.json"),
        ),
        patch.object(dynamic_entry, "datetime", ReplayClock),
        patch.object(averaging_orders, "is_cooling", lambda _side: False),
        patch.object(averaging_orders, "set_cooling", lambda _side: None),
        patch.object(averaging_orders, "generate_pxy_tag", broker.next_tag),
        patch.object(counter_pipe, "_find_script", lambda name: name),
        patch.object(counter_pipe, "_is_executable", lambda _path: True),
        patch.object(counter_pipe, "_load_locks", return_value={}),
        patch.object(counter_pipe, "_mark_lock", lambda _key: None),
        patch.object(counter_pipe, "_fires_today", return_value=0),
        patch.object(counter_pipe, "_count_fire", lambda: None),
        patch.object(counter_pipe, "datetime", ReplayClock),
        patch.object(squareoff_pipe, "datetime", ReplayClock),
        patch("subprocess.Popen", simulated_popen),
        patch("subprocess.run", simulated_squareoff),
        patch.dict(sys.modules, {"runexacpxy": temporary_daily_purge}),
    ]
    with redirect_stdout(output), redirect_stderr(output):
        with ExitStack() as stack:
            for patcher in patchers:
                stack.enter_context(patcher)
            exit_pipe.run_snapshot()
            entry_pipe.main()
            avg_pipe.run_snapshot()
    logged = output.getvalue()
    if logged:
        with runtime_log.open("a", encoding="utf-8") as stream:
            stream.write(f"\n===== {timestamp} =====\n{logged}")
    return logged


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
    history, session_date, trades, decisions, trade_path, decision_path, runtime_log
):
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
        "Production dashboard, exit, entry, averaging, counter-leg, and square-off "
        "pipe code runs against an in-memory simulated broker. Orders are filled "
        "at the following candle open using CE/PE spot-point/premium proxies."
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
    print(f"Production pipe runtime log: {runtime_log}")
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
    output_dir = output_dir or Path.home() / "pxy-backtest-results"
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    runtime_log = output_dir / (
        f"nifty-pipe-replay-{session_date}-{datetime.now():%Y%m%d-%H%M%S}.log"
    )
    with runtime_log.open("w", encoding="utf-8") as stream:
        stream.write(
            "Production pipe output for simulated replay. "
            "No live broker session or external order process is permitted.\n"
        )
    broker = SimulatedBroker()
    decisions = []
    with tempfile.TemporaryDirectory(prefix="pxy-walk-forward-") as temporary_state:
        state_dir = Path(temporary_state)
        for bar in bars:
            timestamp = bar["next_timestamp"]
            fill_spot = bar["next_open"]
            if timestamp is None or fill_spot is None:
                continue
            execution_time = timestamp.time().replace(tzinfo=None)
            if not MARKET_OPEN <= execution_time <= MARKET_CLOSE:
                continue
            before = broker.position_summary()
            first_new_order = len(broker.orders)
            if bar["snapshot_log"]:
                with runtime_log.open("a", encoding="utf-8") as stream:
                    stream.write(
                        f"\n===== PRODUCTION DASHBOARD {bar['timestamp']} =====\n"
                        f"{bar['snapshot_log']}"
                    )
            pipe_output = run_production_pipes(
                bar["snapshot"],
                timestamp,
                float(fill_spot),
                broker,
                state_dir,
                runtime_log,
            )
            current_orders = broker.orders[first_new_order:]
            after = broker.position_summary()
            decisions.append(
                {
                    "timestamp": bar["timestamp"],
                    "execution_timestamp": timestamp,
                    "spot": bar["spot"],
                    "execution_spot": float(fill_spot),
                    "entry_signal": bar["entry"],
                    "exit_signal": bar["exit"],
                    "position_before": before,
                    "position_after": after,
                    "orders_created": len(current_orders),
                    "order_tags": "|".join(order["GuiOrdId"] for order in current_orders),
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
        history, session_date, trades, decisions, trade_path, decision_path, runtime_log
    )
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
