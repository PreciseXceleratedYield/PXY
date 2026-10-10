import csv
import unittest
from datetime import datetime
from pathlib import Path
import sys
import tempfile

SYS_DIR = Path(__file__).resolve().parents[1]
if str(SYS_DIR) not in sys.path:
    sys.path.insert(0, str(SYS_DIR))

from tstmodepxy.broker_sim import SimulatedBroker
from tstmodepxy.backtest import score_spot_points, write_session_csvs


class SimulatedBrokerTests(unittest.TestCase):
    def setUp(self):
        self.broker = SimulatedBroker()
        self.broker.set_market(datetime(2025, 1, 6, 9, 17), 22000)

    def place(self, side, option, tag, quantity=None):
        if quantity is None:
            quantity = self.broker.quantity
        return self.broker.place_order(
            trading_symbol=f"NIFTY-WF-{option}",
            transaction_type=side,
            quantity=quantity,
            tag=tag,
        )

    def test_buy_quote_sell_and_trade_ledger_use_index_spot(self):
        buy = self.place("B", "CE", "WF0000001")
        self.assertEqual(buy["stat"], "Ok")
        self.assertEqual(buy["data"]["orderId"], "WF0000001")
        self.assertEqual(self.broker.orders[-1]["avgPrc"], 22000)
        self.assertEqual(self.broker.position_summary(), "1CE0PE")

        self.broker.set_market(datetime(2025, 1, 6, 9, 18), 22012)
        quote = self.broker.quotes(
            [{"instrument_token": "SIM-CE"}], quote_type="depth"
        )[0]
        self.assertEqual(quote["last_price"], 22012)
        self.assertEqual(
            self.place("S", "CE", "WF0000001_S001")["stat"],
            "Ok",
        )
        self.assertEqual(self.broker.orders[-1]["avgPrc"], 22012)

        self.assertEqual(self.broker.position_summary(), "0CE0PE")
        self.assertEqual(len(self.broker.order_report()["data"]), 2)
        trade = self.broker.trades()[0]
        self.assertEqual(trade["side"], "CE")
        self.assertEqual(trade["index_points_per_unit"], 12)
        self.assertEqual(trade["quantity"], 1)

    def test_put_fill_and_quote_use_raw_index_spot(self):
        self.place("B", "PE", "WF0000002")
        self.broker.set_market(datetime(2025, 1, 6, 9, 18), 21990)
        quote = self.broker.quotes(
            [{"instrument_token": "SIM-PE"}], quote_type="depth"
        )[0]
        self.assertEqual(quote["last_price"], 21990)
        self.place("S", "PE", "WF0000002_S002")
        self.assertEqual(self.broker.orders[-1]["avgPrc"], 21990)
        self.assertEqual(self.broker.trades()[0]["index_points_per_unit"], 10)

    def test_spot_point_score_is_directional_and_quantity_weighted(self):
        self.assertEqual(score_spot_points("CE", 22000, 22050, 75), 3750)
        self.assertEqual(score_spot_points("PE", 22050, 22000, 75), 3750)
        self.assertEqual(score_spot_points("CE", 22050, 22000, 75), -3750)
        with self.assertRaisesRegex(ValueError, "side must be CE or PE"):
            score_spot_points("XX", 22000, 22050, 75)

    def test_rejects_invalid_orders_and_oversells(self):
        self.assertEqual(self.place("B", "CE", "WF0000003", 0)["stat"], "Not_Ok")
        self.assertEqual(
            self.place("S", "CE", "WF0000003_S003")["stat"],
            "Not_Ok",
        )
        self.assertEqual(self.place("B", "XX", "WF0000004")["stat"], "Not_Ok")

    def test_csv_backed_broker_records_each_simulated_fill(self):
        with tempfile.TemporaryDirectory(prefix="pxy-broker-csv-test-") as temp:
            orders_path = Path(temp) / "orders.csv"
            broker = SimulatedBroker(orders_csv=orders_path)
            broker.set_market(datetime(2025, 1, 6, 9, 17), 22000)
            broker.place_order(
                trading_symbol="NIFTY-WF-CE",
                transaction_type="B",
                quantity=broker.quantity,
                tag="WF0000001",
            )

            with orders_path.open(newline="", encoding="utf-8") as stream:
                rows = list(csv.DictReader(stream))
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["trdSym"], "NIFTY-WF-CE")
            self.assertEqual(rows[0]["entry_spot"], "22000.0")
            self.assertEqual(rows[0]["avgPrc"], "22000.0")
            restored = SimulatedBroker(orders_csv=orders_path)
            self.assertEqual(restored.position_summary(), "1CE0PE")

    def test_csv_writer_accepts_pipe_trade_and_bar_records(self):
        with tempfile.TemporaryDirectory(prefix="pxy-csv-test-") as temp:
            trade_path, bars_path = write_session_csvs(
                Path(temp),
                "2025-01-06",
                [{
                    "session": "2025-01-06", "side": "CE",
                    "entry_time": "09:17", "exit_time": "09:18",
                    "entry_spot": 100, "exit_spot": 101, "points": 1,
                    "spot_points_per_unit": 1,
                    "exit_reason": "target_exit", "quantity": 1,
                }],
                [{
                    "timestamp": "09:16", "execution_timestamp": "09:17",
                    "spot": 100, "execution_spot": 101, "entry_signal": "BUY",
                    "exit_signal": "BULL", "position_before": "0CE0PE",
                    "position_after": "1CE0PE", "orders_created": 1,
                    "order_tags": "WF0000001",
                }],
            )
            self.assertIn("spot_points_per_unit", trade_path.read_text())
            self.assertNotIn("simulated_option_entry", trade_path.read_text())
            self.assertIn("execution_timestamp", bars_path.read_text())


if __name__ == "__main__":
    unittest.main()
