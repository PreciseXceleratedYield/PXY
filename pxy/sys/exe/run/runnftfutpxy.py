import json
from runclntpxy import get_session

def get_nifty_future_live_price(client, token: str, segment: str = "nse_fo") -> float:
    """
    Fetches the precise live price of the NIFTY Future contract 
    using your working options depth processing structure.
    """
    try:
        instr = [{"instrument_token": str(token), "exchange_segment": segment}]
        
        # Pull market depth payload exactly like your working options method
        res = client.quotes(instrument_tokens=instr, quote_type="depth")

        if not res or not isinstance(res, list) or len(res) == 0:
            print("Error: Empty or invalid payload array.")
            return 0.0
        
        data = res[0]
        depth = data.get("depth", {})
        buy_list = depth.get("buy", [])
        sell_list = depth.get("sell", [])

        # Process the bid/ask spread
        bid = float(buy_list[0].get("price", 0)) if buy_list else 0.0
        ask = float(sell_list[0].get("price", 0)) if sell_list else 0.0
        
        if bid > 0 and ask > 0:
            return round((bid + ask) / 2, 2)
        
        # Fallback to the last traded price if depth arrays are blank
        return float(data.get("last_price", 0))
    except Exception as e:
        print(f"Tracking error: {e}")
        return 0.0

if __name__ == "__main__":
    # 1. Initialize session using your client script
    session = get_session()
    
    if session:
        # 2. Assign the exact NIFTY Future numerical token for the current month
        # (Look up this 5-digit number on your Kotak App or Watchlist info panel)
        NIFTY_CURRENT_FUTURE_TOKEN = "YOUR_5_DIGIT_FUTURE_TOKEN" 
        
        # 3. Pull the calculated execution price
        live_price = get_nifty_future_live_price(session, token=NIFTY_CURRENT_FUTURE_TOKEN)
        
        print("\n================================")
        print(f"NIFTY FUTURE LIVE PRICE: {live_price}")
        print("================================\n")
    else:
        print("Failed to authenticate session context.")



