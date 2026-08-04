#!/usr/bin/env python3
import sys

def get_position_summary(client=None):
    """
    Corrected for Neo V2 field names and efficiency.
    Now reflects ACTUAL LOT counts for NIFTY (65) and BANKNIFTY (30).
    Returns format: "XCEYPE" (e.g., "2CE0PE", "1CE1PE")
    """
    # ---------------------------------------------------------
    # ⚙️ CONFIGURABLE MANUAL OFFSETS (Set these to fix ghost positions)
    # If the API incorrectly says you have 1 CE, set offset_ce_lots = 1
    # ---------------------------------------------------------
    offset_ce_lots = 1  # Subtracts this many lots from the CE total
    offset_pe_lots = 0  # Subtracts this many lots from the PE total
    # ---------------------------------------------------------

    ce_lots = 0
    pe_lots = 0

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

            # --- ACTIVE POSITION CHECK ---
            if abs(net_qty) > 0:
                # --- Normalize symbol ---
                symbol = str(pos.get("trdSym", "")).upper()
                
                # --- DETECT INDEX & LOT SIZE ---
                # We check BANKNIFTY first because "NIFTY" is a substring of "BANKNIFTY"
                if "BANKNIFTY" in symbol:
                    lot_size = 30
                elif "NIFTY" in symbol:
                    lot_size = 65
                else:
                    # Skip symbols that are not Nifty or Bank Nifty
                    continue

                # --- CALCULATE LOTS ---
                # Divide quantity by lot size to get count (e.g., 130 / 65 = 2)
                current_lots = int(abs(net_qty) / lot_size)

                # --- UPDATE COUNTERS ---
                if symbol.endswith("CE"):
                    ce_lots += current_lots
                elif symbol.endswith("PE"):
                    pe_lots += current_lots

    except Exception as e:
        print(f"❌ Position Error: {e}")
        return "0CE0PE"

    # --- APPLY MANUAL CONFIGURABLE OFFSETS ---
    # max(0, ...) ensures the count never goes below 0 into negative numbers
    ce_lots = max(0, ce_lots - offset_ce_lots)
    pe_lots = max(0, pe_lots - offset_pe_lots)

    # Return the actual lot totals
    return f"{ce_lots}CE{pe_lots}PE"

# ---------------- STANDALONE TEST ----------------
if __name__ == "__main__":
    try:
        from runclntpxy import get_session
        broker = get_session()
        print("Actual Lot Summary:", get_position_summary(broker))
    except Exception as e:
        print(f"❌ Test Run Error: {e}")


