import sys
# Recommend passing the client as an argument instead of calling get_session() here
# from runclntpxy import get_session 

def get_position_summary(client=None):
    """
    Corrected for Neo V2 field names and efficiency.
    """
    ce_flag = 0
    pe_flag = 0
    
    # If no client is passed, we fallback (not recommended for loops)
    if client is None:
        from runclntpxy import get_session
        client = get_session()
        if not client: return "0CE0PE"

    try:
        # Fetch positions
        pos_res = client.positions()
        
        # Neo V2 response structure: {'stat': 'Ok', 'data': [...]}
        positions = pos_res.get("data", [])
        
        if not isinstance(positions, list):
            return "0CE0PE"

        for pos in positions:
            # V2 FIX: Use 'net_qty' or calculate from filled quantities
            # Most V2 versions use 'net_qty' as a string or float
            net_qty = float(pos.get("net_qty", 0))
            
            # If net_qty isn't there, fallback to calculating it
            if net_qty == 0:
                buy = float(pos.get("flBuyQty", 0))
                sell = float(pos.get("flSellQty", 0))
                net_qty = buy - sell

            symbol = pos.get("trdSym", "")
            
            if net_qty != 0:
                if "CE" in symbol:
                    ce_flag = 1
                elif "PE" in symbol:
                    pe_flag = 1
                    
    except Exception as e:
        # print(f"❌ Error checking positions: {e}")
        return "0CE0PE"

    return f"{ce_flag}CE{pe_flag}PE"

if __name__ == "__main__":
    # For standalone testing
    from runclntpxy import get_session
    broker = get_session()
    print(get_position_summary(broker))

