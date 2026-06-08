#!/usr/bin/env python3
import sys
import json
from pathlib import Path  # Safe cross-platform path handling

def get_position_summary(client=None):
    """
    Corrected for Neo V2 field names and efficiency.
    Now reflects ACTUAL LOT counts for NIFTY (65) and BANKNIFTY (30).
    Returns format: "XCEYPE" (e.g., "2CE0PE", "1CE1PE")
    """
    ce_lots = 0
    pe_lots = 0
    position_dumps = []  # Resets cleanly on every function call

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
            # --- Normalize symbol and quantity ---
            symbol = str(pos.get("trdSym", "")).upper()
            net_qty = float(pos.get("net_qty", 0))
            
            # Fallback if broker doesn't send net_qty properly
            if net_qty == 0:
                buy = float(pos.get("flBuyQty", 0))
                sell = float(pos.get("flSellQty", 0))
                net_qty = buy - sell

            # --- DETERMINE STATUS BASED ON QTY ---
            status = "OPEN" if abs(net_qty) > 0 else "CLOSE"

            # --- DUMP ALL POSITIONS (ALL symbols, OPEN or CLOSED) ---
            # Kotak Neo v2 clears floating PNL on closed items. 
            # We calculate PNL via (Total Sell Value - Total Buy Value) to bypass API reset limitations.
            try:
                buy_val = float(pos.get("flBuyAmt", 0)) + float(pos.get("cfBuyAmt", 0))
                sell_val = float(pos.get("flSellAmt", 0)) + float(pos.get("cfSellAmt", 0))
                
                if status == "CLOSE":
                    pnl_val = sell_val - buy_val
                else:
                    pnl_val = float(pos.get("urmtom", pos.get("pnl", sell_val - buy_val)))
            except Exception:
                pnl_val = float(pos.get("urmtom", pos.get("pnl", 0)))

            position_dumps.append({
                "SYMBOL": symbol,
                "QTY": net_qty,
                "PNL": float(pnl_val),
                "STATUS": status
            })

            # --- ORIGINAL ACTIVE POSITION CHECK FOR LOTS ---
            if abs(net_qty) > 0:
                # --- DETECT INDEX & LOT SIZE ---
                # We check BANKNIFTY first because "NIFTY" is a substring of "BANKNIFTY"
                if "BANKNIFTY" in symbol:
                    lot_size = 30
                elif "NIFTY" in symbol:
                    lot_size = 65
                else:
                    # Skip symbols that are not Nifty or Bank Nifty for lot counters
                    continue

                # --- CALCULATE LOTS ---
                # Divide quantity by lot size to get count (e.g., 130 / 65 = 2)
                current_lots = int(abs(net_qty) / lot_size)

                # --- UPDATE COUNTERS ---
                if symbol.endswith("CE"):
                    ce_lots += current_lots
                elif symbol.endswith("PE"):
                    pe_lots += current_lots

        # 🟢 FIXED: Target the 4th parent folder correctly to reach ~/pxy
        # parents[0] = run/, parents[1] = exe/, parents[2] = sys/, parents[3] = pxy/
        target_dir = Path(__file__).resolve().parents[3]
        target_file = target_dir / "livpos.json"

        # Quietly write JSON output to the target directory
        with open(target_file, "w") as f:
            json.dump(position_dumps, f)

    except Exception as e:
        print(f"❌ Position Error: {e}")
        return "0CE0PE"

    # Return the actual lot totals (UNCHANGED ORIGINAL RETURN VALUE)
    return f"{ce_lots}CE{pe_lots}PE"

# ---------------- STANDALONE TEST ----------------
if __name__ == "__main__":
    try:
        from runclntpxy import get_session
        broker = get_session()
        print("Actual Lot Summary:", get_position_summary(broker))
    except Exception as e:
        print(f"❌ Test Run Error: {e}")

