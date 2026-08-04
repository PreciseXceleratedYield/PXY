#!/usr/bin/env python3
import sys

def get_position_summary(client=None):
    """
    Corrected for Neo V2 field names, data types, and closed position logic.
    Reflects LOT counts for NIFTY (65) and BANKNIFTY (30).
    Returns format: "XCEYPE" (e.g., "2CE0PE", "1CE1PE")
    """
    ce_lots = 0
    pe_lots = 0
    
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
        pos_res = client.positions()
        # Handle cases where response might be a dictionary or a direct list
        positions = pos_res.get("data", []) if isinstance(pos_res, dict) else pos_res
        
        if not isinstance(positions, list):
            return "0CE0PE"
            
        for pos in positions:
            # 1. Safely parse quantities to float to handle string responses
            try:
                net_qty = float(pos.get("net_qty", 0))
            except (ValueError, TypeError):
                net_qty = 0.0

            # 2. Fallback check if net_qty is reported as 0 but has buy/sell mismatch
            if net_qty == 0.0:
                try:
                    buy = float(pos.get("flBuyQty", 0))
                    sell = float(pos.get("flSellQty", 0))
                    net_qty = buy - sell
                except (ValueError, TypeError):
                    net_qty = 0.0

            # 3. ACTIVE POSITION CHECK (Ignore completely if net_qty is 0)
            if abs(net_qty) <= 0.001:
                continue

            # 4. Normalize symbol strings
            symbol = str(pos.get("trdSym", "")).upper().strip()
            
            # 5. DETECT INDEX & LOT SIZE
            if "BANKNIFTY" in symbol:
                lot_size = 30
            elif "NIFTY" in symbol:
                lot_size = 65
            else:
                continue  # Skip non-index symbols

            # 6. CALCULATE LOTS
            current_lots = int(round(abs(net_qty) / lot_size))
            if current_lots == 0:
                continue

            # 7. UPDATE COUNTERS (Use 'in' or split check for expiry variations)
            if "CE" in symbol:
                ce_lots += current_lots
            elif "PE" in symbol:
                pe_lots += current_lots
                
    except Exception as e:
        print(f"❌ Position Error: {e}")
        return "0CE0PE"
        
    return f"{ce_lots}CE{pe_lots}PE"

if __name__ == "__main__":
    try:
        from runclntpxy import get_session
        broker = get_session()
        print("Actual Lot Summary:", get_position_summary(broker))
    except Exception as e:
        print(f"❌ Test Run Error: {e}")
