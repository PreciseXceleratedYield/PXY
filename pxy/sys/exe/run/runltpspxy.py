def get_mid_price(client, token: str, segment: str = "nse_fo") -> float:
    try:
        instr = [{"instrument_token": str(token), "exchange_segment": segment}]
        # Using 'depth' as confirmed in your raw test
        res = client.quotes(instrument_tokens=instr, quote_type="depth")

        # FIX 1: Access the first element of the LIST
        if not res or not isinstance(res, list) or len(res) == 0:
            return 0.0
        
        data = res[0] # This unwraps the [ ]
        
        # FIX 2: Drill into 'depth' -> 'buy'/'sell' which are also LISTS
        depth = data.get("depth", {})
        buy_list = depth.get("buy", [])
        sell_list = depth.get("sell", [])

        # FIX 3: Get 'price' from the first dictionary in the list
        # And convert the String '226.3000' to a Float
        bid = float(buy_list[0].get("price", 0)) if buy_list else 0.0
        ask = float(sell_list[0].get("price", 0)) if sell_list else 0.0
        
        if bid > 0 and ask > 0:
            return round((bid + ask) / 2, 2)
        
        # Fallback to LTP if available in this quote type
        return float(data.get("last_price", 0))
    except Exception:
        return 0.0

