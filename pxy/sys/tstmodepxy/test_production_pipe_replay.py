import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

SYS_DIR = Path(__file__).resolve().parents[1]
if str(SYS_DIR) not in sys.path:
    sys.path.insert(0, str(SYS_DIR))

import pytz
from unittest.mock import patch

from tstmodepxy.broker_sim import SimulatedBroker
from tstmodepxy.replay_adapter import ProductionPipeReplay


class ProductionPipeReplayTests(unittest.TestCase):
    def test_production_pipe_sources_do_not_import_backtest_adapters(self):
        production_exe = SYS_DIR / "exe"
        for source in production_exe.glob("*.py"):
            contents = source.read_text(encoding="utf-8")
            with self.subTest(source=source.name):
                self.assertNotIn("replay_adapter", contents)
                self.assertNotIn("SimulatedBroker", contents)

    def test_adapter_restores_process_hooks_after_exit(self):
        system_call = __import__("os").system
        process_run = __import__("subprocess").run
        with tempfile.TemporaryDirectory(prefix="pxy-adapter-scope-test-") as temp:
            with ProductionPipeReplay(
                SYS_DIR, SimulatedBroker(), Path(temp) / "state"
            ):
                self.assertIsNot(__import__("os").system, system_call)
                self.assertIsNot(__import__("subprocess").run, process_run)
        self.assertIs(__import__("os").system, system_call)
        self.assertIs(__import__("subprocess").run, process_run)

    def test_entry_averaging_and_scheduled_squareoff_are_simulated(self):
        timezone = pytz.timezone("Asia/Kolkata")
        broker = SimulatedBroker()
        snapshot = {
            "entry": "BUY",
            "exit": "BULL",
            "atr": 5,
            "price": 22000,
            "direction": "UP",
            "market_data_available": True,
            "ce_force": 1.2,
            "pe_force": 1.2,
        }

        with tempfile.TemporaryDirectory(prefix="pxy-pipe-replay-test-") as temp:
            root = Path(temp)
            runtime_log = root / "pipes.log"
            state_dir = root / "state"
            runtime_log.write_text("pipe replay log\n", encoding="utf-8")
            with patch("sysmodepxy.RUNMODE", "SIM"), ProductionPipeReplay(
                SYS_DIR, broker, state_dir
            ) as engine:
                engine.run_tick(
                    snapshot,
                    timezone.localize(datetime(2025, 1, 6, 9, 17)),
                    22000,
                    runtime_log,
                )
                self.assertEqual([order["trnsTp"] for order in broker.orders], ["B"])

                snapshot["entry"] = "NONE"
                engine.run_tick(
                    snapshot,
                    timezone.localize(datetime(2025, 1, 6, 9, 18)),
                    21902,
                    runtime_log,
                )
                self.assertEqual([order["trnsTp"] for order in broker.orders], ["B", "B"])

                snapshot["exit"] = "BEAR"
                engine.run_tick(
                    snapshot,
                    timezone.localize(datetime(2025, 1, 6, 9, 19)),
                    21902,
                    runtime_log,
                )
                self.assertEqual(
                    [(order["trnsTp"], order["trdSym"]) for order in broker.orders],
                    [
                        ("B", "NIFTY-WF-CE"),
                        ("B", "NIFTY-WF-CE"),
                        ("S", "NIFTY-WF-CE"),
                        ("B", "NIFTY-WF-PE"),
                    ],
                )

                engine.run_tick(
                    snapshot,
                    timezone.localize(datetime(2025, 1, 6, 15, 14)),
                    21900,
                    runtime_log,
                )
                self.assertIn("CE Averaged", runtime_log.read_text(encoding="utf-8"))
                log_text = runtime_log.read_text(encoding="utf-8")
                self.assertIn("FIRED COUNTER-BUY: pxybuype", log_text)
                self.assertIn("ORDER ACCEPTED BY BROKER", log_text)
                self.assertTrue(runtime_log.stat().st_size > 0)

        self.assertEqual(
            [order["trnsTp"] for order in broker.orders],
            ["B", "B", "S", "B", "S", "S"],
        )
        self.assertEqual(broker.position_summary(), "0CE0PE")
        self.assertEqual(len(broker.trades()), 3)


if __name__ == "__main__":
    unittest.main()
