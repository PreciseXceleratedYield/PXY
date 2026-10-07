import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import datetime
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytz

SYS_DIR = Path(__file__).resolve().parents[1]
if str(SYS_DIR) not in sys.path:
    sys.path.insert(0, str(SYS_DIR))

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

    def test_sim_replay_applies_configured_static_risk_target(self):
        with tempfile.TemporaryDirectory(prefix="pxy-sim-risk-target-") as temp:
            broker = SimulatedBroker()
            broker.set_market(
                pytz.timezone("Asia/Kolkata").localize(datetime(2025, 1, 6, 10, 0)),
                22000,
            )
            broker.place_order(
                trading_symbol="NIFTY-WF-CE",
                transaction_type="B",
                quantity=75,
                tag="SIM-SEED",
            )
            open_df = pd.DataFrame(
                [{
                    "Symbol": "NIFTY-WF-CE",
                    "Qty": 75,
                    "Tag": "SIM-SEED",
                    "BUY_PRC": 100,
                    "SELL_PRC": 126.67,
                    "PNL": 2000,
                }]
            )
            closed_df = pd.DataFrame()
            with ProductionPipeReplay(
                SYS_DIR, broker, Path(temp) / "state"
            ) as engine:
                engine.timestamp = broker.current_time
                with patch.object(engine.risk_math, "RISK_MODE", "STATIC"):
                    for minute in range(3):
                        engine.timestamp = broker.current_time.replace(
                            minute=minute,
                        )
                        engine._execute_risk_ledger(broker, open_df, closed_df)

            self.assertTrue(engine.risk_exit_fired)
            self.assertEqual(broker.position_summary(), "0CE0PE")
            self.assertEqual(engine.risk_pnl_offset, 2000)

    def test_sim_replay_counts_breach_only_once_per_bar_timestamp(self):
        with tempfile.TemporaryDirectory(prefix="pxy-sim-risk-tick-") as temp:
            broker = SimulatedBroker()
            broker.set_market(
                pytz.timezone("Asia/Kolkata").localize(datetime(2025, 1, 6, 10, 0)),
                22000,
            )
            broker.place_order(
                trading_symbol="NIFTY-WF-CE",
                transaction_type="B",
                quantity=75,
                tag="SIM-SEED",
            )
            open_df = pd.DataFrame(
                [{
                    "Symbol": "NIFTY-WF-CE",
                    "Qty": 75,
                    "Tag": "SIM-SEED",
                    "BUY_PRC": 100,
                    "SELL_PRC": 126.67,
                    "PNL": 2000,
                }]
            )
            with ProductionPipeReplay(
                SYS_DIR, broker, Path(temp) / "state"
            ) as engine, patch.object(engine.risk_math, "RISK_MODE", "STATIC"):
                engine.timestamp = broker.current_time
                for _ in range(3):
                    engine._execute_risk_ledger(broker, open_df, pd.DataFrame())
                self.assertEqual(engine.risk_breach_ticks, 1)
                self.assertFalse(engine.risk_exit_fired)

                for minute in (1, 2):
                    engine.timestamp = broker.current_time.replace(minute=minute)
                    engine._execute_risk_ledger(broker, open_df, pd.DataFrame())

            self.assertTrue(engine.risk_exit_fired)
            self.assertEqual(broker.position_summary(), "0CE0PE")

    def test_sim_peak_mode_holds_risk_until_original_activation_time(self):
        from datetime import time
        from tstmodepxy import replay_adapter

        with tempfile.TemporaryDirectory(prefix="pxy-sim-risk-peak-") as temp:
            broker = SimulatedBroker()
            timestamp = pytz.timezone("Asia/Kolkata").localize(
                datetime(2025, 1, 6, 10, 0)
            )
            broker.set_market(timestamp, 22000)
            broker.place_order(
                trading_symbol="NIFTY-WF-CE",
                transaction_type="B",
                quantity=75,
                tag="SIM-SEED",
            )
            open_df = pd.DataFrame(
                [{
                    "Symbol": "NIFTY-WF-CE",
                    "Qty": 75,
                    "Tag": "SIM-SEED",
                    "BUY_PRC": 100,
                    "SELL_PRC": 126.67,
                    "PNL": 2000,
                }]
            )
            with (
                patch.object(replay_adapter, "RUNEXACPXY_RISK_MODE", "PEAK"),
                patch.object(replay_adapter, "RUNEXACPXY_CNTRLRSKBAR", "YES"),
                patch.object(
                    replay_adapter,
                    "RUNEXACPXY_CNTRLRSKBAR_ACTIVATION_TIME",
                    time(13, 15),
                ),
                ProductionPipeReplay(SYS_DIR, broker, Path(temp) / "state") as engine,
                patch.object(engine.risk_math, "RISK_MODE", "PEAK"),
            ):
                engine._execute_risk_ledger(broker, open_df, pd.DataFrame())
                self.assertEqual(engine.risk_breach_ticks, 0)
                self.assertEqual(broker.position_summary(), "75CE0PE")

                engine.timestamp = timestamp.replace(hour=13, minute=15)
                engine._execute_risk_ledger(broker, open_df, pd.DataFrame())

            self.assertTrue(engine.risk_control_activated)
            self.assertEqual(engine.risk_pnl_offset, 2000)
            self.assertEqual(engine.risk_breach_ticks, 0)
            self.assertEqual(broker.position_summary(), "75CE0PE")

    def test_lilo_handles_empty_broker_order_report_as_idle(self):
        with tempfile.TemporaryDirectory(prefix="pxy-lilo-empty-orders-") as temp:
            broker = SimulatedBroker()
            with ProductionPipeReplay(
                SYS_DIR, broker, Path(temp) / "state"
            ) as engine:
                with patch.object(
                    broker,
                    "order_report",
                    return_value={"stat": "Ok", "stCode": "200", "data": []},
                ), redirect_stdout(StringIO()) as output:
                    open_df, closed_df = engine.lilo._process_lilo_orders_production(
                        broker, strict=True
                    )

            self.assertTrue(open_df.empty)
            self.assertTrue(closed_df.empty)
            self.assertIn("No order rows returned", output.getvalue())
            self.assertNotIn("TAG MATCH ERROR", output.getvalue())

    def test_lilo_treats_kotak_no_data_response_as_idle(self):
        with tempfile.TemporaryDirectory(prefix="pxy-lilo-no-data-") as temp:
            broker = SimulatedBroker()
            no_data_response = {
                "stCode": 5203,
                "errMsg": "No Data",
                "desc": "data not found",
                "stat": "Not_Ok",
            }
            with ProductionPipeReplay(
                SYS_DIR, broker, Path(temp) / "state"
            ) as engine:
                with patch.object(
                    broker, "order_report", return_value=no_data_response
                ), redirect_stdout(StringIO()) as output:
                    open_df, closed_df = engine.lilo._process_lilo_orders_production(
                        broker, strict=True
                    )

            self.assertTrue(open_df.empty)
            self.assertTrue(closed_df.empty)
            self.assertIn("order report has no data", output.getvalue())
            self.assertNotIn("Invalid Kotak order report response", output.getvalue())
            self.assertNotIn("TAG MATCH ERROR", output.getvalue())

    def test_lilo_still_rejects_other_unsuccessful_order_report_responses(self):
        with tempfile.TemporaryDirectory(prefix="pxy-lilo-invalid-orders-") as temp:
            broker = SimulatedBroker()
            invalid_response = {
                "stCode": 5203,
                "errMsg": "Session expired",
                "desc": "data not found",
                "stat": "Not_Ok",
            }
            with ProductionPipeReplay(
                SYS_DIR, broker, Path(temp) / "state"
            ) as engine, patch.object(
                broker, "order_report", return_value=invalid_response
            ):
                with self.assertRaisesRegex(
                    RuntimeError, "Invalid Kotak order report response"
                ):
                    engine.lilo._process_lilo_orders_production(
                        broker, strict=True
                    )

    def test_entry_pipe_scenarios_are_driven_by_market_snapshot_rows(self):
        scenarios = pd.DataFrame(
            [
                {"name": "flat CE buy", "entry": "BUY", "held": None, "expected": "NIFTY-WF-CE"},
                {"name": "flat PE sell", "entry": "SELL", "held": None, "expected": "NIFTY-WF-PE"},
                {"name": "invalid signal", "entry": "HOLD", "held": None, "expected": None},
                {"name": "occupied CE", "entry": "BUY", "held": "NIFTY-WF-CE", "expected": None},
                {"name": "occupied PE", "entry": "SELL", "held": "NIFTY-WF-PE", "expected": None},
                {"name": "broker session unavailable", "entry": "BUY", "held": None, "expected": None, "session": False},
                {"name": "preopen blackout", "entry": "BUY", "held": None, "expected": None, "minute": 15},
            ]
        )
        timezone = pytz.timezone("Asia/Kolkata")

        for scenario in scenarios.to_dict("records"):
            with self.subTest(scenario=scenario["name"]), tempfile.TemporaryDirectory(
                prefix="pxy-entry-scenario-"
            ) as temp:
                broker = SimulatedBroker()
                minute_value = scenario.get("minute")
                minute = int(minute_value) if pd.notna(minute_value) else 0
                timestamp = timezone.localize(
                    datetime(
                        2025, 1, 6,
                        9 if minute else 10,
                        minute,
                    )
                )
                broker.set_market(timestamp, 22000)
                if scenario["held"]:
                    broker.place_order(
                        trading_symbol=scenario["held"],
                        transaction_type="B",
                        quantity=75,
                        tag="CHK-SEED",
                    )

                with ProductionPipeReplay(
                    SYS_DIR, broker, Path(temp) / "state"
                ) as engine:
                    engine.timestamp = timestamp
                    engine.snapshot = {"entry": scenario["entry"]}
                    session_patch = (
                        patch.object(engine.entry_pipe, "get_session", return_value=None)
                        if pd.notna(scenario.get("session")) and not scenario["session"]
                        else patch.object(engine.entry_pipe, "get_session", return_value=broker)
                    )
                    with session_patch, redirect_stdout(StringIO()):
                        engine.entry_pipe.main()

                new_orders = [
                    order for order in broker.orders
                    if order["GuiOrdId"] != "CHK-SEED"
                ]
                self.assertEqual(
                    [order["trdSym"] for order in new_orders],
                    [scenario["expected"]]
                    if pd.notna(scenario["expected"])
                    else [],
                )

    def test_exit_pipe_scenarios_consume_active_order_dataframes(self):
        scenarios = pd.DataFrame([
            {
                "name": "target hit",
                "held": ("CE",),
                "available": True,
                "exit": "SIDE",
                "sell_price": 120.0,
                "target": 110.0,
                "expected": [("B", "NIFTY-WF-CE"), ("S", "NIFTY-WF-CE")],
                "invalid_positions": False,
            },
            {
                "name": "market snapshot unavailable",
                "held": ("CE",),
                "available": False,
                "exit": "SIDE",
                "sell_price": 120.0,
                "target": 110.0,
                "expected": [("B", "NIFTY-WF-CE")],
                "invalid_positions": False,
            },
            {
                "name": "invalid broker positions block target sell",
                "held": ("CE",),
                "available": True,
                "exit": "SIDE",
                "sell_price": 120.0,
                "target": 110.0,
                "expected": [("B", "NIFTY-WF-CE")],
                "invalid_positions": True,
            },
            {
                "name": "target not reached; hostile CE signal",
                "held": ("CE",),
                "available": True,
                "exit": "BEAR",
                "sell_price": 100.0,
                "target": 110.0,
                "expected": [("B", "NIFTY-WF-CE"), ("B", "NIFTY-WF-PE")],
            },
            {
                "name": "both legs held; no counter-buy",
                "held": ("CE", "PE"),
                "available": True,
                "exit": "BEAR",
                "sell_price": 100.0,
                "target": 110.0,
                "expected": [
                    ("B", "NIFTY-WF-CE"),
                    ("B", "NIFTY-WF-PE"),
                ],
            },
        ])
        timezone = pytz.timezone("Asia/Kolkata")

        for scenario in scenarios.to_dict("records"):
            with self.subTest(scenario=scenario["name"]), tempfile.TemporaryDirectory(
                prefix="pxy-exit-scenario-"
            ) as temp:
                broker = SimulatedBroker()
                timestamp = timezone.localize(datetime(2025, 1, 6, 10, 0))
                broker.set_market(timestamp, 22000)
                order_rows = []
                for side in scenario["held"]:
                    symbol = f"NIFTY-WF-{side}"
                    tag = f"CHK-{side}"
                    broker.place_order(
                        trading_symbol=symbol,
                        transaction_type="B",
                        quantity=75,
                        tag=tag,
                    )
                    order_rows.append(
                        {
                            "symbol": symbol,
                            "qty": 75,
                            "tag": tag,
                            "buy_time": timestamp,
                            "buy_prc": 100.0,
                            "sell_prc": scenario["sell_price"],
                            "pnl": 200.0 if scenario["sell_price"] >= 110 else 0.0,
                            "pxy_tgt": scenario["target"],
                            "exit": scenario["exit"],
                            "atr": 5.0,
                        }
                    )
                active_orders = pd.DataFrame(order_rows)

                with ProductionPipeReplay(
                    SYS_DIR, broker, Path(temp) / "state"
                ) as engine:
                    engine.timestamp = timestamp
                    invalid_positions = (
                        pd.notna(scenario.get("invalid_positions"))
                        and bool(scenario["invalid_positions"])
                    )
                    positions_patch = (
                        patch.object(
                            broker,
                            "positions",
                            return_value={"stat": "Not_Ok", "data": []},
                        )
                        if invalid_positions
                        else patch.object(broker, "positions", wraps=broker.positions)
                    )
                    with positions_patch, patch.object(
                            engine.exit_pipe,
                            "get_combined_data",
                            return_value={
                                "active_orders": active_orders,
                                "market_snapshot_available": scenario["available"],
                            },
                        ), redirect_stdout(StringIO()):
                        engine.exit_pipe.run_snapshot()

                actual = [(order["trnsTp"], order["trdSym"]) for order in broker.orders]
                self.assertEqual(actual, scenario["expected"])

    def test_averaging_pipe_scenarios_consume_loss_and_position_dataframes(self):
        scenarios = pd.DataFrame(
            [
                {"name": "CE loss triggers average", "side": "CE", "sell_price": 90.0, "max_layers": 5, "cooling": False, "expected": 2},
                {"name": "PE loss triggers average", "side": "PE", "sell_price": 90.0, "max_layers": 5, "cooling": False, "expected": 2},
                {"name": "profit does not average", "side": "CE", "sell_price": 105.0, "max_layers": 5, "cooling": False, "expected": 1},
                {"name": "maximum layers blocks average", "side": "CE", "sell_price": 90.0, "max_layers": 1, "cooling": False, "expected": 1},
                {"name": "cooldown blocks average", "side": "PE", "sell_price": 90.0, "max_layers": 5, "cooling": True, "expected": 1},
            ]
        )
        timezone = pytz.timezone("Asia/Kolkata")

        for scenario in scenarios.to_dict("records"):
            with self.subTest(scenario=scenario["name"]), tempfile.TemporaryDirectory(
                prefix="pxy-average-scenario-"
            ) as temp:
                broker = SimulatedBroker()
                timestamp = timezone.localize(datetime(2025, 1, 6, 10, 0))
                broker.set_market(timestamp, 22000)
                symbol = f"NIFTY-WF-{scenario['side']}"
                broker.place_order(
                    trading_symbol=symbol,
                    transaction_type="B",
                    quantity=75,
                    tag="CHK-AVERAGE",
                )
                active_orders = pd.DataFrame(
                    [
                        {
                            "symbol": symbol,
                            "qty": 75,
                            "tag": "CHK-AVERAGE",
                            "buy_time": timestamp,
                            "buy_prc": 100.0,
                            "pxy_entry": 100.0,
                            "sell_prc": scenario["sell_price"],
                            "pnl": (scenario["sell_price"] - 100.0) * 75,
                            "exit": "SIDE",
                            "atr": 5.0,
                        }
                    ]
                )
                if scenario["expected"] == 2:
                    opposite_side = "PE" if scenario["side"] == "CE" else "CE"
                    opposite_symbol = f"NIFTY-WF-{opposite_side}"
                    broker.place_order(
                        trading_symbol=opposite_symbol,
                        transaction_type="B",
                        quantity=75,
                        tag="CHK-AVERAGE-OPPOSITE",
                    )
                    active_orders = pd.concat(
                        [
                            active_orders,
                            pd.DataFrame(
                                [
                                    {
                                        "symbol": opposite_symbol,
                                        "qty": 75,
                                        "tag": "CHK-AVERAGE-OPPOSITE",
                                        "buy_time": timestamp,
                                        "buy_prc": 100.0,
                                        "pxy_entry": 100.0,
                                        "sell_prc": 110.0,
                                        "pnl": 750.0,
                                        "exit": "SIDE",
                                        "atr": 5.0,
                                    }
                                ]
                            ),
                        ],
                        ignore_index=True,
                    )

                with ProductionPipeReplay(
                    SYS_DIR, broker, Path(temp) / "state"
                ) as engine:
                    engine.timestamp = timestamp
                    with (
                        patch.object(engine.avg_controller, "calculate_lgt", return_value=-5.0),
                        patch.object(engine.averaging_orders, "MAX_LAYERS", scenario["max_layers"]),
                        patch.object(
                            engine.averaging_orders,
                            "is_cooling",
                            side_effect=lambda side: scenario["cooling"] and side == scenario["side"],
                        ),
                        redirect_stdout(StringIO()),
                    ):
                        engine.avg_controller.handle_side_averaging(broker, active_orders)

                expected_order_count = scenario["expected"] + int(scenario["expected"] == 2)
                self.assertEqual(len(broker.orders), expected_order_count)
                if scenario["expected"] == 2:
                    self.assertEqual(broker.orders[-1]["trdSym"], symbol)

    def test_squareoff_pipe_flattens_the_supplied_positions_dataframe(self):
        timezone = pytz.timezone("Asia/Kolkata")
        timestamp = timezone.localize(datetime(2025, 1, 6, 15, 26))
        broker = SimulatedBroker()
        broker.set_market(timestamp, 22000)
        broker.place_order(
            trading_symbol="NIFTY-WF-CE",
            transaction_type="B",
            quantity=75,
            tag="CHK-SQUAREOFF",
        )
        active_orders = pd.DataFrame(
            [
                {
                    "symbol": "NIFTY-WF-CE",
                    "qty": 75,
                    "tag": "CHK-SQUAREOFF",
                    "buy_time": timestamp,
                }
            ]
        )

        with tempfile.TemporaryDirectory(prefix="pxy-squareoff-scenario-") as temp:
            with ProductionPipeReplay(
                SYS_DIR, broker, Path(temp) / "state"
            ) as engine:
                engine.timestamp = timestamp
                with (
                    patch.object(engine.squareoff_pipe, "get_session", return_value=broker),
                    patch.object(
                        engine.squareoff_pipe,
                        "get_combined_data",
                        return_value={
                            "active_orders": active_orders,
                            "market_snapshot": pd.DataFrame(),
                        },
                    ),
                    patch.object(engine.squareoff_pipe, "datetime", engine.ReplayClock),
                    patch.object(engine.squareoff_pipe.sys, "argv", ["exesqrpxy.py", "-all"]),
                    redirect_stdout(StringIO()),
                ):
                    engine.squareoff_pipe.exit_all_positions()

        self.assertEqual(
            [(order["trnsTp"], order["trdSym"]) for order in broker.orders],
            [("B", "NIFTY-WF-CE"), ("S", "NIFTY-WF-CE")],
        )

    def test_engine_tick_sequence_replays_market_and_active_order_dataframes(self):
        timezone = pytz.timezone("Asia/Kolkata")
        snapshots = pd.DataFrame(
            [
                {"timestamp": datetime(2025, 1, 6, 10, 0), "spot": 22000.0, "entry": "BUY", "exit": "BULL"},
                {"timestamp": datetime(2025, 1, 6, 10, 1), "spot": 22001.0, "entry": "NONE", "exit": "BEAR"},
                {"timestamp": datetime(2025, 1, 6, 10, 2), "spot": 22002.0, "entry": "NONE", "exit": "BEAR"},
            ]
        )
        broker = SimulatedBroker()
        with tempfile.TemporaryDirectory(prefix="pxy-engine-sequence-") as temp:
            runtime_log = Path(temp) / "pipes.log"
            runtime_log.write_text("CHK production-pipe scenario replay\n", encoding="utf-8")
            with ProductionPipeReplay(
                SYS_DIR, broker, Path(temp) / "state"
            ) as engine:
                for index, market_row in snapshots.iterrows():
                    timestamp = timezone.localize(market_row["timestamp"])
                    broker.set_market(timestamp, market_row["spot"])
                    active_rows = []
                    if index >= 1:
                        active_rows.append(
                            {
                                "symbol": "NIFTY-WF-CE",
                                "qty": 75,
                                "tag": "WF0000001",
                                "buy_time": timezone.localize(datetime(2025, 1, 6, 10, 0)),
                                "buy_prc": 100.0,
                                "pxy_entry": 100.0,
                                "sell_prc": 100.0,
                                "pnl": 0.0,
                                "pxy_tgt": 110.0,
                                "exit": market_row["exit"],
                                "atr": 5.0,
                            }
                        )
                    if index >= 2:
                        active_rows.append(
                            {
                                "symbol": "NIFTY-WF-PE",
                                "qty": 75,
                                "tag": "WF0000002",
                                "buy_time": timezone.localize(datetime(2025, 1, 6, 10, 1)),
                                "buy_prc": 100.0,
                                "pxy_entry": 100.0,
                                "sell_prc": 100.0,
                                "pnl": 0.0,
                                "pxy_tgt": 110.0,
                                "exit": market_row["exit"],
                                "atr": 5.0,
                            }
                        )
                    order_frame = pd.DataFrame(active_rows)
                    pipe_data = {
                        "active_orders": order_frame,
                        "market_snapshot_available": True,
                    }
                    market_snapshot = {
                        "entry": market_row["entry"],
                        "exit": market_row["exit"],
                        "atr": 5.0,
                        "price": market_row["spot"],
                        "direction": "UP",
                        "market_data_available": True,
                        "ce_force": 1.2,
                        "pe_force": 1.2,
                    }
                    with (
                        patch.object(engine.exit_pipe, "get_combined_data", return_value=pipe_data),
                        patch.object(engine.avg_pipe, "get_combined_data", return_value=pipe_data),
                    ):
                        engine.run_tick(
                            market_snapshot,
                            timestamp,
                            market_row["spot"],
                            runtime_log,
                        )

                    expected_positions = ("75CE0PE", "75CE75PE", "75CE75PE")[index]
                    self.assertEqual(broker.position_summary(), expected_positions)

            self.assertIn("CHK production-pipe scenario replay", runtime_log.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
