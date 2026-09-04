import json
from datetime import datetime
import calendar
from runclntpxy import get_session

def get_current_month_future_symbol():
    """
    Dynamically constructs the exact text symbol name Kotak expects 
    for the current month's NIFTY Future contract.
    Example output format: NIFTY24SEPFUT
    """
    now = datetime.now()
    year_short = now.strftime("%y")     # e.g., '26'
    month_abc = now.strftime("%b").upper() # e.g., 'SEP'
    
    # Check if we have passed the last Thursday of the current month
    # If yes, we need to roll over to the next month's contract dynamically
    c = calendar.Calendar(firstweekday=calendar.MONDAY)
    month_cal = c.monthdatescalendar(now.year, now.month)
    
    # Extract the last Thursday date
    last_thursday = [
        day for week in month_cal 
        for day in week if day.weekday() == calendar.THURSDAY and day.month == now.month
    ][-1]
    
    # If today is past the last Thursday trading cutoff, roll over to the next month
    if now.date() > last_thursday:
        next_month = now.month + 1 if now.month < 12 else 1
        next_year = now.year if now.month < 12 else now.year + 1
        next_date = datetime(next_year, next_month, 1)
        year_short = next_date.strftime("%y")
        month_abc = next_date.strftime("%b").upper()

    constructed_symbol = f"NIFTY{year_short}{month_abc}FUT"
    return constructed_symbol

def main():
    # 1. Construct the target symbol text
    target_symbol = get_current_month_future_symbol()
    print(f"1. Constructed target text symbol: {target_symbol}")

    # 2. Authenticate session
    session = get_session()
    if not session:
        return

    try:
        print(f"2. Fetching the exact token ID for {target_symbol}...")
        
        # Pull only this one explicit symbol match from the server
        search_result = session.search_scrip(
            exchange_segment="nse_fo", 
            symbol=target_symbol
        )
        
        if not search_result or 'data' not in search_result or not search_result['data']:
            print("Error: Could not retrieve a token match for this specific constructed symbol name.")
            return

        # Isolate the precise match row
        contract_data = search_result['data'][0]
        token = contract_data.get('instrument_token') or contract_data.get('pSymbolToken')
        trading_symbol = contract_data.get('trading_symbol') or contract_data.get('pTrdSymbol')
        
        print(f"Target Token Found -> Name: {trading_symbol} | Token ID: {token}")

        # 3. Pull live market OHLC data metrics using the isolated straight token
        print("3. Querying latest market quotes payload...")
        instrument_payload = [
            {
                "instrument_token": str(token),
                "exchange_segment": "nse_fo"
            }
        ]
        
        quote_response = session.quotes(
            instrument_tokens=instrument_payload,
            quote_type="ohlc"
        )

        print("\n===== NIFTY FUTURE LATEST OHLC =====")
        print(json.dumps(quote_response, indent=4))

    except Exception as e:
        print(f"API Execution Failure: {e}")

if __name__ == "__main__":
    main()



