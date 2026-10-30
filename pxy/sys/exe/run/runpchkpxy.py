
#!/usr/bin/env python3

import math
import sys
from pathlib import Path
import traceback

SYS_DIR = Path(__file__).resolve().parents[2]
if str(SYS_DIR) not in sys.path:
    sys.path.insert(0, str(SYS_DIR))

from syscnfgpxy import RUNPCHKPXY_DEBUG_ENABLED, RUNPCHKPXY_NIFTY_LOT_SIZE

DEBUG = RUNPCHKPXY_DEBUG_ENABLED
LOT_SIZE = RUNPCHKPXY_NIFTY_LOT_SIZE


def _parse_quantity(value):
    quantity = float(str(value if value is not None else 0).replace(",", "").strip())

    if not math.isfinite(quantity):
        raise ValueError(f"Invalid quantity: {value}")

    return quantity


def _get_position_summary(pos_res):
    """
    Calculate active NIFTY CE/PE positions.

    Returns:
        "XCEYPE" when positions are verified.
        None when positions cannot be verified.
    """

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

    if status and status not in {"ok", "success", "successful"}:
        print(f"❌ Position check failed: broker status {status}.")
        return None

    positions = pos_res.get("data")

    if not isinstance(positions, list):
        print("❌ Position check skipped: invalid positions data.")
        return None

    ce_qty = 0.0
    pe_qty = 0.0

    if DEBUG:
        print("\n[Position debug] NIFTY option positions:")

    try:
        for pos in positions:

            if not isinstance(pos, dict):
                raise ValueError("Invalid position row.")

            symbol = str(pos.get("trdSym", "")).upper().strip()

            if not symbol.startswith("NIFTY"):
                continue

            if not (symbol.endswith("CE") or symbol.endswith("PE")):
                continue

            # Calculate actual net quantity.
            if pos.get("net_qty") is not None:
                net_qty = _parse_quantity(pos["net_qty"])
            else:
                cf_buy = _parse_quantity(pos.get("cfBuyQty", 0))
                cf_sell = _parse_quantity(pos.get("cfSellQty", 0))
                fl_buy = _parse_quantity(pos.get("flBuyQty", 0))
                fl_sell = _parse_quantity(pos.get("flSellQty", 0))

                net_qty = cf_buy + fl_buy - cf_sell - fl_sell

            if net_qty == 0:
                if DEBUG:
                    print(f"{symbol}: CLOSED (0)")
                continue

            active_qty = abs(net_qty)

            if symbol.endswith("CE"):
                ce_qty += active_qty
                side = "CE"
            else:
                pe_qty += active_qty
                side = "PE"

            if DEBUG:
                print(
                    f"{symbol}: ACTIVE | "
                    f"Side={side} | Net Qty={net_qty}"
                )

        # Count lots separately for each side.
        ce_lots = math.ceil(ce_qty / LOT_SIZE)
        pe_lots = math.ceil(pe_qty / LOT_SIZE)

        if DEBUG:
            print(f"\nCE Active Quantity: {ce_qty}")
            print(f"PE Active Quantity: {pe_qty}")
            print(f"CE Lots: {ce_lots}")
            print(f"PE Lots: {pe_lots}")

        return f"{ce_lots}CE{pe_lots}PE"

    except Exception as e:
        print(f"❌ Position calculation failed: {e}")

        if DEBUG:
            traceback.print_exc()

        return None


def get_position_summary(client=None):
    """
    Returns CE/PE position counts as 'XCEYPE'.
    Returns None when positions cannot be verified.
    """

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
        return _get_position_summary(pos_res)

    except Exception as e:
        print(f"❌ Position check failed: {e}")

        if DEBUG:
            traceback.print_exc()

        return None


if __name__ == "__main__":

    try:
        from runclntpxy import get_session

        broker = get_session()

        if not broker:
            raise RuntimeError("No broker session.")

        print("\n" + "=" * 65)
        print("KOTAK ACTIVE POSITION CHECK")
        print("=" * 65)

        # Fetch positions only once.
        response = broker.positions()

        print(f"Broker Status: {response.get('stat') if isinstance(response, dict) else 'Invalid'}")

        summary = _get_position_summary(response)

        print("\n" + "=" * 65)
        print("PXY ACTIVE POSITION SUMMARY")
        print("=" * 65)

        if summary is None:
            print("Position Summary: UNAVAILABLE")
        else:
            print(f"Actual Lot Summary: {summary}")

        print("=" * 65 + "\n")

    except Exception as e:
        print(f"❌ Test Run Error: {e}")

        if DEBUG:
            traceback.print_exc()
