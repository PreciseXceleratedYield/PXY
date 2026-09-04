import json
import calendar
from datetime import datetime
from colorama import Fore, Style, init
from runclntpxy import get_session

# Initialize colorama terminal formatting hooks
init(autoreset=True)

def get_current_month_future_symbol():
    """
    Dynamically constructs the exact text symbol name Kotak expects 
    for the current month's NIFTY Future contract, accounting for 
    automated last-Thursday rollover logic.
    """
    now = datetime.now()
    year_short = now.strftime("%y")       # e.g., '26'
    month_abc = now.strftime("%b").upper() # e.g., 'SEP'
    
    # Calculate the last Thursday of the current month
    c = calendar.Calendar(firstweekday=calendar.MONDAY)
    month_cal = c.monthdatescalendar(now.year, now.month)
    
    last_thursday = [
        day for week in month_cal 
        for day in week if day.weekday() == calendar.THURSDAY and day.month == now.month
    ][-1]
    
    # If today is past the last Thursday trading cutoff, roll over to the next contract month
    if now.date() > last_thursday:
        next_month = now.month + 1 if now.month < 12 else 1
        next_year = now.year if now.month < 12 else now.year + 1
        next_date = datetime(next_year, next_month, 1)
        year_short = next_date.strftime("%y")
        month_abc = next_date.strftime("%b").upper()

    return f"NIFTY{year_short}{month_abc}FUT"

def fetch_nifty_future_ohlc():
    # 1. Initialize your established session wrapper
    session = get_session()
    if not session:
        print(f"{Fore.RED}❌ Authentication Failed: Session could not be initialized.")
        return

    try:
        # 2. Generate the deterministic text symbol contract name
        target_symbol = get_current_month_future_symbol()
        print(f"📡 Target Created: {Fore.CYAN}{target_symbol}")
        print("🔍 Querying server for numeric token assignment...")
        
        # 3. Targeted micro-search using exact match parameters to protect RAM limits
        search_result = session.search_scrip(
            exchange_segment="nse_fo", 
            symbol=target_symbol
        )
        
        if not search_result or 'data' not in search_result or not search_result['data']:
            print(f"{Fore.RED}❌ Error: No token data payload returned for {target_symbol}.")
            return

        # Extract structural dictionary data frames safely
        scrip_data = search_result['data']
        token = scrip_data.get("instrument_token") or scrip_data.get("pSymbolToken")
        trading_symbol = scrip_data.get("trading_symbol") or scrip_data.get("pTrdSymbol")
        
        if not token:
            print(f"{Fore.RED}❌ Error: Structural token key parsing mapping failure.")
            return

        print(f"🎯 Target Locked: {Fore.GREEN}{trading_symbol} {Fore.WHITE}(Token ID: {token})")
        print("📈 Requesting live market OHLC data metrics...")

        # 4. Request the light, optimized OHLC data dictionary block
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

        # 5. Output Clean Terminal Visual Payload
        print(f"\n{Fore.YELLOW}================ NIFTY FUTURE LIVE OHLC ================")
        print(json.dumps(quote_response, indent=4))
        print(f"{Fore.YELLOW}========================================================")

    except Exception as e:
        print(f"{Fore.RED}❌ Execution Engine Crash: {e}")

if __name__ == "__main__":
    fetch_nifty_future_ohlc()

