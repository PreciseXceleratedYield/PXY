"""Backtest-only adapter for running production pipes against simulated services."""

import importlib
import io
import os
import sys
from contextlib import ExitStack, redirect_stderr, redirect_stdout
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pandas as pd

from syscnfgpxy import (
    RUNEXACPXY_BREACH_TICKS_REQUIRED,
    RUNEXACPXY_CNTRLRSKBAR,
    RUNEXACPXY_CYCLE_TARGET_PCT,
    RUNEXACPXY_TARGET_SQUAREOFF_ENABLED,
)


class ProductionPipeReplay:
    """Bind production pipe dependencies to historical data and a simulated broker.

    The production modules are imported unchanged. All replay substitutions are
    scoped to this adapter's lifetime and never written into production modules.
    """

    def __init__(self, sys_dir, broker, state_dir, *, risk_bar_enabled=True):
        self.sys_dir = Path(sys_dir)
        self.broker = broker
        self.state_dir = Path(state_dir)
        self.timestamp = None
        self.snapshot = None
        self.output = None
        self.stack = ExitStack()

        exe_dir = self.sys_dir / "exe"
        run_dir = exe_dir / "run"
        for path in (exe_dir, run_dir):
            if str(path) not in sys.path:
                sys.path.insert(0, str(path))

        exists = os.path.exists
        squareoff_log = (self.sys_dir.parent / "web" / "websqrpxy.json").resolve()

        def exists_without_production_squareoff_state(path):
            try:
                if Path(path).resolve() == squareoff_log:
                    return False
            except (TypeError, OSError):
                pass
            return exists(path)

        with patch("os.path.exists", exists_without_production_squareoff_state):
            self.entry_pipe = importlib.import_module("exeentrpxy")
            self.exit_pipe = importlib.import_module("exeexitpxy")
            self.avg_pipe = importlib.import_module("exeavgpxy")
            self.oms = importlib.import_module("exeomspxy")
            self.lilo = importlib.import_module("runlilopxy")
        self.avg_controller = importlib.import_module("exeavxpxy")
        self.averaging_orders = importlib.import_module("exeamspxy")
        self.counter_pipe = importlib.import_module("execbuypxy")
        self.squareoff_pipe = importlib.import_module("exesqrpxy")
        self.dynamic_entry = importlib.import_module("exedynpxy")
        self.risk_math = importlib.import_module("runexmtpxy")
        self.risk_control_activated = False
        self.risk_pnl_offset = 0.0
        self.risk_peak = 0.0
        self.risk_breach_ticks = 0
        self.risk_exit_fired = False
        self.risk_last_counted_timestamp = None
        self.risk_bar_enabled = risk_bar_enabled
        self.risk_cycle_started_at = None
        self.risk_cycle_tags = set()

        class ReplayClock(datetime):
            @classmethod
            def now(cls, tz=None):
                current = self.timestamp
                if hasattr(current, "to_pydatetime"):
                    current = current.to_pydatetime()
                if tz is None:
                    return current.replace(tzinfo=None)
                if current.tzinfo is None:
                    return current.replace(tzinfo=tz)
                return current.astimezone(tz)

        self.ReplayClock = ReplayClock

        def production_dispatch(_name, provider, *args, **kwargs):
            kwargs.pop("test_kwargs", None)
            return provider(*args, **kwargs)

        def get_snapshot():
            return self.snapshot

        def simulated_shell(command):
            name = Path(str(command).strip().split()[0]).name
            if name == "pxybuyce":
                self._place_simulated_buy("CE", "WF")
            elif name == "pxybuype":
                self._place_simulated_buy("PE", "WF")
            else:
                raise RuntimeError(
                    f"Unexpected production shell command blocked: {command}"
                )
            return 0

        def simulated_popen(command, *args, **kwargs):
            command_path = Path(command[0]).name if isinstance(command, (list, tuple)) else ""
            if command_path == "pxybuyce":
                self._place_simulated_buy("CE", "CB")
            elif command_path == "pxybuype":
                self._place_simulated_buy("PE", "CB")
            elif isinstance(command, (list, tuple)) and any(
                Path(str(part)).name == "sysddmppxy.py" for part in command
            ):
                pass
            else:
                raise RuntimeError(
                    f"Unexpected production process launch blocked: {command}"
                )
            return SimpleNamespace(pid=0, returncode=0)

        def simulated_squareoff(command, *args, **kwargs):
            command = list(command) if isinstance(command, (list, tuple)) else [command]
            command_name = Path(str(command[0])).name
            if command_name in {"pxysqrce", "pxysqrpe"}:
                all_args = ["-ce" if command_name == "pxysqrce" else "-pe"]
            elif command_name == "exesqrpxy.py" or any(
                str(part).endswith("exesqrpxy.py") for part in command
            ):
                all_args = [
                    str(part) for part in command[1:]
                    if not str(part).endswith("exesqrpxy.py")
                ]
            else:
                raise RuntimeError(
                    f"Unexpected production subprocess blocked: {command}"
                )
            with patch.object(
                self.squareoff_pipe, "get_session", return_value=self.broker
            ), patch.object(
                self.squareoff_pipe, "get_combined_data", self.oms.get_combined_data
            ), patch.object(
                self.squareoff_pipe, "datetime", self.ReplayClock
            ), patch.object(
                self.squareoff_pipe, "subprocess"
            ) as squareoff_subprocess, patch.object(
                self.squareoff_pipe.sys,
                "argv",
                ["exesqrpxy.py", *all_args],
            ):
                squareoff_subprocess.Popen.return_value = SimpleNamespace(pid=0)
                success = self.squareoff_pipe.exit_all_positions()
            return SimpleNamespace(returncode=0 if success is not False else 1)

        risk_ledger_hook = (
            self._execute_risk_ledger
            if self.risk_bar_enabled
            else lambda *args, **kwargs: None
        )
        temporary_daily_purge = SimpleNamespace(
            daily_purge_check=lambda: None,
            execute_master_risk_ledger=risk_ledger_hook,
        )
        self.state_dir.mkdir(parents=True, exist_ok=True)
        patchers = [
            patch.object(self.entry_pipe, "get_all_data", get_snapshot),
            patch.object(self.entry_pipe, "get_session", return_value=broker),
            patch.object(
                self.entry_pipe,
                "get_position_summary",
                lambda _client: broker.position_summary(),
            ),
            patch.object(self.entry_pipe, "dispatch_mode", production_dispatch),
            patch.object(self.entry_pipe.os, "system", simulated_shell),
            patch.object(self.entry_pipe, "datetime", ReplayClock),
            patch.object(self.exit_pipe, "get_combined_data", self.oms.get_combined_data),
            patch.object(self.exit_pipe, "get_session", return_value=broker),
            patch.object(self.exit_pipe, "dispatch_mode", production_dispatch),
            patch.object(self.exit_pipe, "ledger_busy", return_value=False),
            patch.object(self.exit_pipe, "datetime", ReplayClock),
            patch.object(self.exit_pipe, "_load_locks", return_value={}),
            patch.object(self.exit_pipe, "_mark_lock", lambda _key: None),
            patch.object(self.exit_pipe, "process_metrics_print_and_dump", lambda *args: None),
            patch.object(self.exit_pipe, "dump_idle_json", lambda *args: None),
            patch.object(self.avg_pipe, "get_combined_data", self.oms.get_combined_data),
            patch.object(self.avg_pipe, "get_session", return_value=broker),
            patch.object(self.avg_pipe, "dispatch_mode", production_dispatch),
            patch.object(self.avg_pipe, "dump_idle_json", lambda *args: None),
            patch.object(self.oms, "dispatch_mode", production_dispatch),
            patch.object(self.oms.syspxy, "get_all_data", get_snapshot),
            patch.object(self.oms, "print_market_dashboard", lambda _market_df: None),
            patch.object(self.oms, "get_session", return_value=broker),
            patch.object(self.lilo, "dispatch_mode", production_dispatch),
            patch.object(self.lilo, "dump_to_json", lambda _df: None),
            patch.object(self.lilo, "dump_livpos_to_json", lambda _rows: None),
            patch.object(self.avg_controller, "datetime", ReplayClock),
            patch.object(self.avg_controller, "ledger_busy", return_value=False),
            patch.object(
                self.avg_controller,
                "get_position_summary",
                lambda _client: broker.position_summary(),
            ),
            patch.object(
                self.avg_controller,
                "WEB_AVG_JSON_REL",
                str(self.state_dir / "webavgpxy.json"),
            ),
            patch.object(self.dynamic_entry, "datetime", ReplayClock),
            patch.object(self.averaging_orders, "is_cooling", lambda _side: False),
            patch.object(self.averaging_orders, "set_cooling", lambda _side: None),
            patch.object(self.averaging_orders, "generate_pxy_tag", broker.next_tag),
            patch.object(self.counter_pipe, "_find_script", lambda name: name),
            patch.object(self.counter_pipe, "_is_executable", lambda _path: True),
            patch.object(self.counter_pipe, "_load_locks", return_value={}),
            patch.object(self.counter_pipe, "_mark_lock", lambda _key: None),
            patch.object(self.counter_pipe, "_fires_today", return_value=0),
            patch.object(self.counter_pipe, "_count_fire", lambda: None),
            patch.object(self.counter_pipe, "datetime", ReplayClock),
            patch.object(self.squareoff_pipe, "datetime", ReplayClock),
            patch.object(self.squareoff_pipe, "start_cooldown", lambda: None),
            patch("subprocess.Popen", simulated_popen),
            patch("subprocess.run", simulated_squareoff),
            patch.dict(sys.modules, {"runexacpxy": temporary_daily_purge}),
        ]
        try:
            self.stack.enter_context(
                patch("os.path.exists", exists_without_production_squareoff_state)
            )
            for patcher in patchers:
                self.stack.enter_context(patcher)
        except Exception:
            self.stack.close()
            raise

    def _place_simulated_buy(self, option, prefix):
        self.broker.place_order(
            trading_symbol=f"NIFTY-WF-{option}",
            transaction_type="B",
            quantity=self.broker.quantity,
            tag=self.broker.next_tag(prefix),
        )

    def _execute_risk_ledger(self, client, open_df, closed_df, exit_signal=None):
        if not self.risk_bar_enabled:
            return

        now = self.timestamp
        if hasattr(now, "to_pydatetime"):
            now = now.to_pydatetime()
        if now == self.risk_last_counted_timestamp:
            return
        self.risk_last_counted_timestamp = now

        open_tags = self.risk_math.cycle_ledger_tags(open_df)
        if not open_tags:
            self.risk_cycle_started_at = None
            self.risk_cycle_tags.clear()
            self.risk_breach_ticks = 0
            return

        if (
            self.risk_cycle_started_at is None
            or not self.risk_cycle_tags
        ):
            self.risk_cycle_started_at = self.risk_math.cycle_start_time(open_df)
            if self.risk_cycle_started_at is None:
                raise RuntimeError(
                    "SIM risk cycle cannot start without an active lot buy timestamp."
                )
            self.risk_cycle_tags = set(open_tags)
            self.risk_breach_ticks = 0
        else:
            self.risk_cycle_tags.update(open_tags)

        metrics = self.risk_math.cycle_risk_metrics(
            open_df,
            closed_df,
            self.risk_cycle_tags,
            exit_signal,
            RUNEXACPXY_CYCLE_TARGET_PCT,
        )
        if not (
            str(RUNEXACPXY_CNTRLRSKBAR).upper().strip() == "YES"
            and RUNEXACPXY_TARGET_SQUAREOFF_ENABLED
        ):
            self.risk_breach_ticks = 0
            return
        if not metrics["target_reached"]:
            self.risk_breach_ticks = 0
            return

        self.risk_breach_ticks += 1
        if self.risk_breach_ticks < RUNEXACPXY_BREACH_TICKS_REQUIRED:
            return
        risk_open_df = open_df.copy()
        risk_open_df.columns = [str(column).upper() for column in risk_open_df.columns]
        for index, row in enumerate(risk_open_df.to_dict("records"), start=1):
            result = client.place_order(
                trading_symbol=row["SYMBOL"],
                transaction_type="S",
                quantity=row["QTY"],
                tag=f"{row['TAG']}_S_RISK{index:03d}",
            )
            if str(result.get("stat", "")).lower() != "ok":
                raise RuntimeError(
                    f"SIM risk exit failed for {row['SYMBOL']} tag {row['TAG']}: {result!r}"
                )
        self.risk_exit_fired = True
        self.risk_breach_ticks = 0
        self.risk_cycle_started_at = None
        self.risk_cycle_tags.clear()
        print(
            f"SIM CYCLE TARGET EXIT: cycle PnL {metrics['cycle_pnl']:.2f}, "
            f"paid {metrics['premium_paid']:.2f}, "
            f"target {metrics['target']:.2f}; "
            f"closed {len(open_df)} active rows."
        )

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return self.stack.__exit__(exc_type, exc_value, traceback)

    def run_tick(self, snapshot, timestamp, spot, runtime_log):
        self.timestamp = timestamp
        self.snapshot = snapshot
        self.broker.set_market(timestamp, spot)
        self.risk_exit_fired = False
        output = io.StringIO()
        self.output = output
        with redirect_stdout(output), redirect_stderr(output):
            self.exit_pipe.run_snapshot()
            if not self.risk_exit_fired:
                self.entry_pipe.main()
            if not self.risk_exit_fired:
                self.avg_pipe.run_snapshot()
        logged = output.getvalue()
        if logged:
            with Path(runtime_log).open("a", encoding="utf-8") as stream:
                stream.write(f"\n===== {timestamp} =====\n{logged}")
        return logged
