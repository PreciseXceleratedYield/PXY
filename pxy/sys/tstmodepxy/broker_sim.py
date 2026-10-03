"""In-memory broker adapter for running production pipes without live orders."""

from datetime import datetime


class SimulatedBroker:
    """Minimal Kotak-shaped client backed only by in-memory simulated orders."""

    quantity = 75
    premium_base = 100.0

    def __init__(self):
        self.orders = []
        self.current_spot = 0.0
        self.current_time = None
        self._tag_counter = 0

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

    def _premium(self, symbol):
        open_orders = self._open_orders(symbol)
        if not open_orders:
            return self.premium_base
        total_qty = sum(order.get("remaining", order["fldQty"]) for order in open_orders)
        if total_qty <= 0:
            return self.premium_base
        avg_entry_spot = sum(
            order["entry_spot"] * order.get("remaining", order["fldQty"])
            for order in open_orders
        ) / total_qty
        delta = self.current_spot - avg_entry_spot
        if symbol.endswith("PE"):
            delta = -delta
        return max(2.0, self.premium_base + delta)

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
            "avgPrc": round(self._premium(symbol), 2),
            "ordDtTm": timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            "GuiOrdId": tag,
            "trdSym": symbol,
            "tok": "SIM-CE" if symbol.endswith("CE") else "SIM-PE",
            "exSeg": "nse_fo",
            "trnsTp": transaction,
            "entry_spot": self.current_spot,
        }
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
        for instrument in instrument_tokens:
            token = str(instrument.get("instrument_token", ""))
            symbol = "NIFTY-WF-CE" if token == "SIM-CE" else "NIFTY-WF-PE"
            premium = round(self._premium(symbol), 2)
            quotes.append(
                {
                    "last_price": premium,
                    "ltp": premium,
                    "depth": {
                        "buy": [{"price": max(0.05, premium - 0.05)}],
                        "sell": [{"price": premium + 0.05}],
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
        """Return completed virtual trades paired by tag, without premium P&L."""
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
                    "simulated_option_entry": buy["avgPrc"],
                    "simulated_option_exit": sell["avgPrc"],
                    "quantity": min(buy["fldQty"], sell["fldQty"]),
                    "index_points_per_unit": index_points,
                    "exit_reason": "production_pipe",
                }
            )
        return trades
