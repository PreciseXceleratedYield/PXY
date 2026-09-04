import json
from datetime import datetime
import calendar
from runclntpxy import get_session

def get_current_month_future_symbol():
    """
    Dynamically constructs the exact text symbol name Kotak expects 
    for the current month's NIFTY Future contract.
    Example format: NIFTY26SEPFUT
    """
    now = datetime.now()
    year_short = now.strftime("%y")       # e.g., '26'
    month_abc = now.strftime("%b").upper() # e.g., 'SEP'
    
    # Check if the market has passed the last Thursday of the current month
    # to roll over to the next month's future contract automatically.
    c = calendar.Calendar(firstweekday=calendar.MONDAY)
    month_cal = c.monthdatescalendar(now.year, now.month)
    
    # Extract the last Thursday date of this month
    last_thursday = [
        day for week in month_cal 
        for day in week if dayweekday() == calendarTHURSDAY and daymonth == nowmonth
    ][-]
    
    # If today is past the last Thursday trading cutoff, roll over to the next month
    if now.date() > last_thursday:
        next_month = now.month + 1 if now.month < 12 else 1
        next_year = now.year if now.month < 12 else now.year + 1
        next_date = datetime(next_year, next_month, 1)
        year_short = next_date.strftime("%y")
        month_abc = next_date.strftime("%b").upper()

    return f"NIFTY{year_short}{month_abc}FUT"


def find_and_get_mid_price(client, symbol_text: str, segment: str = "nse_fo") -> float:
    """
    1. Finds the token for the constructed future symbol text.
    2. Uses your exact working options processing structure with quote_type="depth".
    """
    try:
        print(f"1. Querying token ID for symbol string: {symbol_text}")
        # Search directly by the exact constructed symbol to return only 1 row
        search_result = client.search_scrip(exchange_segment=segment, symbol=symbol_text)
        
        if not search_result or 'data' not in search_result or len(search_result['data']) == 0:
            print(f"Error: Symbol {symbol_text} not found on server search.")
            return 0.0

        # Unpack the first object from search result data list to get token
        scrip_data = search_result['data'] if isinstance(search_result['data'], list) else search_result['data']
        token = scrip_data.get("instrument_token") or scrip_data.get("pSymbolToken")
        trading_symbol = scrip_data.get("trading_symbol") or scrip_data.get("pTrdSymbol")
        
        print(f"2. Found Live Token: {token} ({trading_symbol})")
        print("3. Fetching live quote metrics via market depth...")

        # Construct payload with found token
        instr = [{"instrument_token": str(token), "exchange_segment": segment}]
        
        # Pull market depth payload exactly like your working options method
        res = client.quotes(instrument_tokens=instr, quote_type="depth")

        # Your exact unwrapping logic
        if not res or not isinstance(res, list) or len(res) == 0:
            return 0.0
        
        data = res 
        
        depth = data.get("depth", {})
        buy_list = depth.get("buy",)
        sell_list = depth.get("sell",)

        # Process bid/ask from your working structure
        bid = float(buy_list.get("price", 0)) if buy_list else 0.0
        ask = float(sell_list.get("price", 0)) if sell_list else 0.0
        
        if bid > 0 and ask > 0:
            return round((bid + ask) / 2, 2)
        
        # Fallback to last_price
        return float(data.get("last_price", 0))
        
    except Exception as e:
        print(f"Execution Error inside logic: {e}")
        return 0.0


def main():
    # 1. Initialize session using runclntpxy.py
    session = get_session()
    if not session:
        print("Failed to authenticate session context.")
        return

    # 2. Get dynamic month symbol text
    target_symbol = get_current_month_future_symbol()

    # 3. Find token and use token to return live price
    live_price = find_and_get_mid_price(session, symbol_text=target_symbol)
    
    print("\n================================")
    print(f"NIFTY FUTURE LIVE PRICE: {live_price}")
    print("================================\n")


if __name__ == "__main__":
    main()

