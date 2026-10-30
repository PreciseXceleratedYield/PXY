
#!/usr/bin/env python3

import math
import os
import traceback
from pprint import pprint

DEBUG = os.environ.get("RUNPCHK_DEBUG") == "1"


def get_position_summary(client=None):
    """
    Returns CE/PE position counts as "XCEYPE".
    Returns None when positions cannot be verified.
    """

    offset_ce_lots = 0
    offset_pe_lots = 0

    if client is None:
        try:
            from runclntpxy import get_session
            client = get_session()
        except Exception as e:
            print(f"❌ Session Error: {e}")
            return None

    if not client:
        print("❌ Position check skipped: no broker session.")
        return None

    try:
        pos_res = client.positions()

        if DEBUG:
            print("\n[Position debug] Raw broker response:")
            pprint(pos_res, sort_dicts=False)

        if not isinstance(pos_res, dict):
            print("❌ Position check skipped: invalid broker response.")
            return None

        status = str(pos_res.get("stat", "")).strip().casefold()
        error_message = str(pos_res.get("errMsg", "")).strip().casefold()

        if (
            status in {"not_ok", "not ok"}
            and error_message == "no data"
            and pos_res.get("data") is None
            and not pos_res.get("error")
        ):
            print("No open positions reported by broker.")
            return "0CE0PE"

        if pos_res.get("errMsg") or pos_res.get("error"):
            print(
                f"❌ Position check failed: "
                f"{pos_res.get('errMsg') or pos_res.get('error')}"
            )
            return None

        status = pos_res.get("stat")

        if status is not None and str(status).strip().lower() not in {
            "ok", "success", "successful"
        }:
            print(f"❌ Position check failed: broker status {status}.")
            return None

        positions = pos_res.get("data")

        if not isinstance(positions, list):
            print("❌ Position check skipped: missing or invalid positions data.")
            return None

        ce_lots = 0
        pe_lots = 0

        def parse_quantity(value):
            quantity = float(str(value).replace(",", "").strip())

            if not math.isfinite(quantity):
                raise ValueError(f"Invalid quantity: {value}")

            return quantity

        for pos in positions:

            if not isinstance(pos, dict):
                raise ValueError("Invalid position row.")

            # Use broker net_qty when available.
            if pos.get("net_qty") is not None:

                net_qty = parse_quantity(pos["net_qty"])

            else:

                # Include carry-forward and today's transactions.
                cf_buy = parse_quantity(pos.get("cfBuyQty", 0))
                cf_sell = parse_quantity(pos.get("cfSellQty", 0))

                fl_buy = parse_quantity(pos.get("flBuyQty", 0))
                fl_sell = parse_quantity(pos.get("flSellQty", 0))

                net_qty = (
                    cf_buy
                    + fl_buy
                    - cf_sell
                    - fl_sell
                )

            # Ignore fully closed positions.
            if net_qty == 0:
                continue

            symbol = str(pos.get("trdSym", "")).upper().strip()

            if not symbol:
                raise ValueError(
                    "Active position row has no trading symbol."
                )

            if not symbol.startswith("NIFTY"):
                continue

            # NIFTY option lot size.
            lot_size = 65

            lots = max(
                1,
                math.ceil(abs(net_qty) / lot_size)
            )

            if symbol.endswith("CE"):
                ce_lots += lots

            elif symbol.endswith("PE"):
                pe_lots += lots

            if DEBUG:
                print(
                    f"[Position debug] {symbol} | "
                    f"CF Buy: {cf_buy if 'cf_buy' in locals() else 'n/a'} | "
                    f"CF Sell: {cf_sell if 'cf_sell' in locals() else 'n/a'} | "
                    f"Net Qty: {net_qty} | Lots: {lots}"
                )

        ce_lots = max(0, ce_lots - offset_ce_lots)
        pe_lots = max(0, pe_lots - offset_pe_lots)

        return f"{ce_lots}CE{pe_lots}PE"

    except Exception as e:
        print(f"❌ Position check failed: {e}")

        if DEBUG:
            traceback.print_exc()

        return None


if __name__ == "__main__":

    try:
        from runclntpxy import get_session

        broker = get_session()

        print("\n" + "=" * 70)
        print("KOTAK ACTUAL BROKER POSITIONS")
        print("=" * 70)

        response = broker.positions()

        if not isinstance(response, dict):

            print("❌ Invalid broker response:")
            pprint(response)

        else:

            print(f"Status : {response.get('stat')}")
            print(f"Message: {response.get('errMsg')}")

            positions = response.get("data")

            if isinstance(positions, list) and positions:

                print(f"\nTotal position rows: {len(positions)}")

                for index, position in enumerate(positions, 1):

                    print(f"\n--- POSITION {index} ---")
                    pprint(position, sort_dicts=False)

            else:

                print("\nNo position rows returned by Kotak.")
                pprint(response, sort_dicts=False)

        print("\n" + "=" * 70)
        print("PXY CE/PE POSITION SUMMARY")
        print("=" * 70)

        print(
            "Actual Lot Summary:",
            get_position_summary(broker)
        )

        print("=" * 70 + "\n")

    except Exception as e:

        print(f"❌ Test Run Error: {e}")
        traceback.print_exc()

