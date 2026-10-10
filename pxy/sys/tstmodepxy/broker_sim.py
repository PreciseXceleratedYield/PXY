"""Simulated broker adapter with an optional CSV-persisted order ledger."""

import csv
from datetime import datetime
from pathlib import Path


class SimulatedBroker:
    """Minimal broker adapter that fills and marks CE/PE trades at index spot."""

    quantity = 65

    def __init__(self, orders_csv=None):
        self.orders = []
        self.current_spot = 0.0
        self.current_time = None
        self._tag_counter = 0
        self.orders_csv = Path(orders_csv) if orders_csv is not None else None
        if self.orders_csv is not None and self.orders_csv.exists():
            with self.orders_csv.open(newline="", encoding="utf-8") as stream:
                for row in csv.DictReader(stream):
                    row["fldQty"] = int(row["fldQty"])
                    row["avgPrc"] = float(row["avgPrc"])
                    row["entry_spot"] = float(row["entry_spot"])
                    self.orders.append(row)

    def set_market(self, timestamp, spot):
        self.current_time = timestamp
        self.current_spot = float(spot)

    def next_tag(self, prefix="WF"):
        self._tag_counter += 1
        return f"{prefix}{self._tag_counter:07d}"

    def _open_orders(self, symbol=None):
        buys = {}
        for order in self.orders:
            if symbol is not None and order["trdSym"] != symbol:
                continue
            if order["trnsTp"] == "B":
                buys.setdefault(
                    order["GuiOrdId"],
                    {**order, "remaining": order["fldQty"]},
                )
        for order in self.orders:
            if order["trnsTp"] != "S":
                continue
            base_tag = order["GuiOrdId"].split("_S", 1)[0]
            buy = buys.get(base_tag)
            if buy:
                buy["remaining"] -= order["fldQty"]
        return [
            order for order in buys.values()
            if order.get("remaining", order["fldQty"]) > 0
        ]

    def place_order(self, **params):
        symbol = str(params.get("trading_symbol", "")).upper().strip()
        transaction = str(params.get("transaction_type", "")).upper().strip()
        if transaction not in {"B", "S"} or not symbol.endswith(("CE", "PE")):
            return {"stat": "Not_Ok", "errMsg": "Invalid simulated order"}
        try:
            quantity = abs(int(float(params.get("quantity", 0))))
        except (TypeError, ValueError, OverflowError):
            return {"stat": "Not_Ok", "errMsg": "Invalid simulated quantity"}
        if quantity <= 0:
            return {"stat": "Not_Ok", "errMsg": "Non-positive simulated quantity"}
        if transaction == "S":
            held = sum(
                order.get("remaining", order["fldQty"])
                for order in self._open_orders(symbol)
            )
            if quantity > held:
                return {"stat": "Not_Ok", "errMsg": "Simulated sell exceeds position"}

        tag = str(params.get("tag") or self.next_tag())
        timestamp = self.current_time or datetime.now()
        order = {
            "ordSt": "complete",
            "fldQty": quantity,
            "avgPrc": self.current_spot,
            "ordDtTm": timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            "GuiOrdId": tag,
            "trdSym": symbol,
            "tok": "SIM-CE" if symbol.endswith("CE") else "SIM-PE",
            "exSeg": "nse_fo",
            "trnsTp": transaction,
            "entry_spot": self.current_spot,
        }
        if self.orders_csv is not None:
            self.orders_csv.parent.mkdir(parents=True, exist_ok=True)
            write_header = (
                not self.orders_csv.exists() or self.orders_csv.stat().st_size == 0
            )
            with self.orders_csv.open("a", newline="", encoding="utf-8") as stream:
                writer = csv.DictWriter(stream, fieldnames=order.keys())
                if write_header:
                    writer.writeheader()
                writer.writerow(order)
        self.orders.append(order)
        return {"stat": "Ok", "stCode": "200", "data": {"orderId": tag}}

    def order_report(self):
        rows = list(self.orders)
        if not rows:
            # Keep the production LILO parser's expected schema for a flat account.
            rows = [{"ordSt": "cancelled"}]
        return {"stat": "Ok", "stCode": "200", "data": rows}

    def positions(self):
        symbols = {order["trdSym"] for order in self.orders}
        rows = []
        for symbol in symbols:
            net = sum(
                order["fldQty"] if order["trnsTp"] == "B" else -order["fldQty"]
                for order in self.orders
                if order["trdSym"] == symbol
            )
            if net:
                rows.append({"trdSym": symbol, "tok": "SIM-CE" if symbol.endswith("CE") else "SIM-PE", "net_qty": net})
        return {"stat": "Ok", "stCode": "200", "data": rows}

    def quotes(self, instrument_tokens, quote_type="ltp"):
        quotes = []
        for _instrument in instrument_tokens:
            spot = self.current_spot
            quotes.append(
                {
                    "last_price": spot,
                    "ltp": spot,
                    "depth": {
                        "buy": [{"price": spot}],
                        "sell": [{"price": spot}],
                    },
                }
            )
        return quotes

    def position_summary(self):
        positions = self.positions()["data"]
        ce = sum(row["net_qty"] for row in positions if row["trdSym"].endswith("CE"))
        pe = sum(row["net_qty"] for row in positions if row["trdSym"].endswith("PE"))
        return f"{ce}CE{pe}PE"

    def trades(self):
        """Return completed virtual trades paired by tag using index-spot fills."""
        def base_tag(tag):
            return str(tag).split("_S", 1)[0].split("_", 1)[0]

        buys = {
            base_tag(order["GuiOrdId"]): order
            for order in self.orders if order["trnsTp"] == "B"
        }
        trades = []
        for sell in (order for order in self.orders if order["trnsTp"] == "S"):
            tag = base_tag(sell["GuiOrdId"])
            buy = buys.get(tag)
            if buy is None:
                continue
            index_points = sell["entry_spot"] - buy["entry_spot"]
            if buy["trdSym"].endswith("PE"):
                index_points = -index_points
            trades.append(
                {
                    "symbol": buy["trdSym"],
                    "side": buy["trdSym"][-2:],
                    "tag": tag,
                    "entry_time": buy["ordDtTm"],
                    "exit_time": sell["ordDtTm"],
                    "entry_spot": buy["entry_spot"],
                    "exit_spot": sell["entry_spot"],
                    "quantity": min(buy["fldQty"], sell["fldQty"]),
                    "index_points_per_unit": index_points,
                    "exit_reason": (
                        "risk_bar"
                        if "_S_RISK" in sell["GuiOrdId"]
                        else "production_exit"
                    ),
                }
            )
        return trades
