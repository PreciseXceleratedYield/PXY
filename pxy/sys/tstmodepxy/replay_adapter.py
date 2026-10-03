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


class ProductionPipeReplay:
    """Bind production pipe dependencies to historical data and a simulated broker.

    The production modules are imported unchanged. All replay substitutions are
    scoped to this adapter's lifetime and never written into production modules.
    """

    def __init__(self, sys_dir, broker, state_dir):
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
            if not isinstance(command, (list, tuple)) or not any(
                str(part).endswith("exesqrpxy.py") for part in command
            ):
                raise RuntimeError(
                    f"Unexpected production subprocess blocked: {command}"
                )
            all_args = [
                str(part) for part in command[1:]
                if not str(part).endswith("exesqrpxy.py")
            ]
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
                self.squareoff_pipe.exit_all_positions()
            return SimpleNamespace(returncode=0)

        temporary_daily_purge = SimpleNamespace(
            daily_purge_check=lambda: None,
            execute_master_risk_ledger=lambda *args, **kwargs: None,
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

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return self.stack.__exit__(exc_type, exc_value, traceback)

    def run_tick(self, snapshot, timestamp, spot, runtime_log):
        self.timestamp = timestamp
        self.snapshot = snapshot
        self.broker.set_market(timestamp, spot)
        output = io.StringIO()
        self.output = output
        with redirect_stdout(output), redirect_stderr(output):
            self.exit_pipe.run_snapshot()
            self.entry_pipe.main()
            self.avg_pipe.run_snapshot()
        logged = output.getvalue()
        if logged:
            with Path(runtime_log).open("a", encoding="utf-8") as stream:
                stream.write(f"\n===== {timestamp} =====\n{logged}")
        return logged
