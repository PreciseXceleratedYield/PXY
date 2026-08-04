#!/usr/bin/env python3
import sys

def get_position_summary(client=None):
    """
    Overnight-safe position parser for Neo V2 API.
    Handles dirty net_qty balances for trades closed the next day.
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
            # 1. Safe float parsing for core variables
            try:
                net_qty = float(pos.get("net_qty", 0))
                fl_buy_qty = float(pos.get("flBuyQty", 0))
                fl_sell_qty = float(pos.get("flSellQty", 0))
                
                # Check Kotak Neo V2 alternative field names just in case
                cf_qty = float(pos.get("cfQty", 0)) 
                day_qty = float(pos.get("dayQty", 0))
            except (ValueError, TypeError):
                net_qty, fl_buy_qty, fl_sell_qty, cf_qty, day_qty = 0.0, 0.0, 0.0, 0.0, 0.0

            # 2. OVERNIGHT CLOSURE OVERRIDE
            # Trap A: Explicit zero check
            if abs(net_qty) <= 0.001:
                continue
                
            # Trap B: Overnight position closed out completely today
            # If you carried 65 shares forward (cfQty) and sold 65 today (flSellQty), your net position is dead.
            if cf_qty != 0 and (cf_qty + (fl_buy_qty - fl_sell_qty)) == 0:
                continue

            # Trap C: Alternative validation using day activity matching net_qty inversion
            if fl_buy_qty == 0 and fl_sell_qty != 0 and abs(net_qty) == fl_sell_qty:
                # This implies the record is only showing today's square-off action, meaning it is closed
                if cf_qty == 0: # If cfQty isn't populated but it's an overnight trade
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

