#!/usr/bin/env python3
import sys

def get_position_summary(client=None):
    """
    Overnight-safe position parser for Neo V2 API.
    Correctly ignores closed positions from previous days.
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
        positions = pos_res.get("data", []) if isinstance(pos_res, dict) else pos_res
        
        if not isinstance(positions, list):
            return "0CE0PE"
            
        for pos in positions:
            # 1. Parse fields safely as floats
            try:
                net_qty = float(pos.get("net_qty", 0))
            except (ValueError, TypeError):
                net_qty = 0.0

            # 2. OVERNIGHT FIX: Read absolute net open quantities directly 
            # Kotak Neo often tracks absolute net open quantities via 'cfQty' (Carried Forward) and 'dayQty'
            # If net_qty is explicitly 0, the position is flat. Do not try to recalculate it.
            if abs(net_qty) <= 0.001:
                continue

            # 3. Normalize trading symbol
            symbol = str(pos.get("trdSym", "")).upper().strip()
            
            # 4. Filter only Nifty and Bank Nifty
            if "BANKNIFTY" in symbol:
                lot_size = 30
            elif "NIFTY" in symbol:
                lot_size = 65
            else:
                continue

            # 5. Calculate actual remaining open lots
            current_lots = int(round(abs(net_qty) / lot_size))
            if current_lots == 0:
                continue

            # 6. Check for contract type anywhere inside the string
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

