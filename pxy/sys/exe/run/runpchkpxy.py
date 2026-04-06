#!/usr/bin/env python3
import sys

def get_position_summary(client=None):
    """
    Corrected for Neo V2 field names and efficiency.
    Returns: "0CE0PE", "1CE0PE", "0CE1PE", "1CE1PE"
    """

    ce_flag = 0
    pe_flag = 0

    # Fallback session (not recommended inside loops)
    if client is None:
        try:
            from runclntpxy import get_session
            client = get_session()
        except Exception as e:
            print(f"❌ Session Error: {e}")
            return "0CE0PE"

        if not client:
            return "0CE0PE"

    try:
        # Fetch positions
        pos_res = client.positions()

        # Expected: {'stat': 'Ok', 'data': [...]}
        positions = pos_res.get("data", [])

        if not isinstance(positions, list):
            return "0CE0PE"

        for pos in positions:

            # --- Get net quantity ---
            net_qty = float(pos.get("net_qty", 0))

            # Fallback if broker doesn't send net_qty properly
            if net_qty == 0:
                buy = float(pos.get("flBuyQty", 0))
                sell = float(pos.get("flSellQty", 0))
                net_qty = buy - sell

            # --- Normalize symbol ---
            symbol = str(pos.get("trdSym", "")).upper()

            # --- ACTIVE POSITION CHECK ---
            if abs(net_qty) > 0:

                # --- SAFE OPTION TYPE CHECK ---
                if symbol.endswith("CE"):
                    ce_flag = 1

                elif symbol.endswith("PE"):
                    pe_flag = 1

    except Exception as e:
        print(f"❌ Position Error: {e}")
        return "0CE0PE"

    return f"{ce_flag}CE{pe_flag}PE"


# ---------------- STANDALONE TEST ----------------
if __name__ == "__main__":
    try:
        from runclntpxy import get_session
        broker = get_session()
        print("Position Summary:", get_position_summary(broker))
    except Exception as e:
        print(f"❌ Test Run Error: {e}")
