#!/usr/bin/env python3
import math
import os
import traceback

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
            if isinstance(pos_res, dict):
                positions = pos_res.get("data")
                row_count = len(positions) if isinstance(positions, list) else "n/a"
                print(
                    "[Position debug] response keys="
                    f"{sorted(pos_res.keys())}, stat={pos_res.get('stat')!r}, "
                    f"errMsg={pos_res.get('errMsg')!r}, "
                    f"error={pos_res.get('error')!r}, "
                    f"data_type={type(positions).__name__}, rows={row_count}"
                )
            else:
                print(
                    "[Position debug] response type="
                    f"{type(pos_res).__name__}"
                )

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
            print(f"❌ Position check failed: {pos_res.get('errMsg') or pos_res.get('error')}")
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

            if pos.get("net_qty") is not None:
                net_qty = parse_quantity(pos["net_qty"])
            elif "flBuyQty" in pos or "flSellQty" in pos:
                net_qty = (
                    parse_quantity(pos.get("flBuyQty", 0))
                    - parse_quantity(pos.get("flSellQty", 0))
                )
            else:
                raise ValueError("Position row has no recognizable quantity.")

            if net_qty == 0 and ("flBuyQty" in pos or "flSellQty" in pos):
                net_qty = (
                    parse_quantity(pos.get("flBuyQty", 0))
                    - parse_quantity(pos.get("flSellQty", 0))
                )

            if net_qty == 0:
                continue

            symbol = str(pos.get("trdSym", "")).upper().strip()
            if not symbol:
                raise ValueError("Active position row has no trading symbol.")

            if not symbol.startswith("NIFTY"):
                continue
            lot_size = 65

            lots = max(1, math.ceil(abs(net_qty) / lot_size))

            if symbol.endswith("CE"):
                ce_lots += lots
            elif symbol.endswith("PE"):
                pe_lots += lots

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
        print("Actual Lot Summary:", get_position_summary(broker))
    except Exception as e:
        print(f"❌ Test Run Error: {e}")
