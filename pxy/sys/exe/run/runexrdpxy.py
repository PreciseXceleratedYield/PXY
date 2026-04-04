import traceback

def get_best_prices(client, symbol):
    """
    Corrected for Kotak Neo V2 response structure.
    """
    try:
        instr = [{"instrument_token": str(symbol), "exchange_segment": "nse_fo"}]
        # V2 uses 'market_depth' or 'depth'
        res = client.quotes(instrument_tokens=instr, quote_type="market_depth")

        # V2 response: res['message'] is often a list or a dict containing 'depth'
        message = res.get("message", [])
        if not message:
            return 0.0, 0.0

        # Handle both list and dict response formats
        data = message[0] if isinstance(message, list) else message
        depth = data.get("depth", {})
        
        # Extracts from the top of the bid/ask stacks
        bid = float(depth.get("buy", [{}])[0].get("price", 0))
        ask = float(depth.get("sell", [{}])[0].get("price", 0))
        
        return bid, ask
    except Exception as e:
        print(f"⚠️ Depth Error: {e}")
        return 0.0, 0.0

def execute_order(client, symbol, qty, side, buffer=5.0):
    """
    Executes with mandatory V2 fields to prevent rejections.
    """
    price_used = 0
    try:
        bid, ask = get_best_prices(client, symbol)

        if bid == 0 and ask == 0:
            # Fallback to LTP if depth is empty
            instr = [{"instrument_token": str(symbol), "exchange_segment": "nse_fo"}]
            ltp_res = client.quotes(instrument_tokens=instr, quote_type="ltp")
            msg = ltp_res.get("message", [])
            data = msg[0] if isinstance(msg, list) else msg
            ltp = float(data.get("last_price", 0))
            
            if ltp == 0:
                return {"stat": "Not_Ok", "errMsg": "No Price Data Found", "price_used": 0}
            price_used = ltp + buffer if side.upper() in ["BUY", "CE"] else ltp - buffer
        else:
            # Buffer against the opposite side for quick execution
            price_used = ask + buffer if side.upper() in ["BUY", "CE"] else bid - buffer

        trans_type = "B" if side.upper() in ["BUY", "CE"] else "S"

        # V2 MANDATORY PARAMETERS
        params = {
            "exchange_segment": "nse_fo",
            "product": "MIS",
            "price": str(round(price_used, 1)),
            "order_type": "L",          # 'L' is standard for Limit in V2
            "quantity": str(qty),
            "validity": "DAY",
            "trading_symbol": symbol,
            "transaction_type": trans_type,
            "amo": "NO",                # Mandatory
            "disclosed_quantity": "0",  # Mandatory
            "market_protection": "0",   # Recommended
            "trigger_price": "0"
        }

        result = client.place_order(**params)
        
        # Attach price used for the dashboard
        if isinstance(result, dict):
            result["price_used"] = price_used
        return result

    except Exception as e:
        return {"stat": "Not_Ok", "errMsg": str(e), "price_used": price_used}


