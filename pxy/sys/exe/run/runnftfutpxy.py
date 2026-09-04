import json
import re
import calendar
from datetime import datetime
from colorama import Fore, Style, init
from runclntpxy import get_session

# Initialize colorama terminal auto-reset formatting hooks
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


def find_and_get_mid_price(client, symbol_text: str, segment: str = "nse_fo") -> float:
    """
    1. Finds the broker-specific numerical token for the constructed future symbol text.
    2. Uses your exact, working option market depth processing structure with quote_type="depth".
    """
    try:
        print(f"📡 Querying Kotak token ID for symbol string: {Fore.CYAN}{symbol_text}")
        
        # Search directly by the exact constructed symbol to return exactly 1 row from the server
        search_result = client.search_scrip(exchange_segment=segment, symbol=symbol_text)
        
        if not search_result or 'data' not in search_result or len(search_result['data']) == 0:
            print(f"{Fore.RED}❌ Error: Symbol {symbol_text} not found on server search.")
            return 0.0

        # Unpack the specific matching contract dictionary safely
        scrip_data = search_result['data']
        token = scrip_data.get("instrument_token") or scrip_data.get("pSymbolToken")
        trading_symbol = scrip_data.get("trading_symbol") or scrip_data.get("pTrdSymbol")
        
        print(f"🎯 Broker Token Located: {Fore.GREEN}{token} {Fore.WHITE}({trading_symbol})")
        print("📈 Fetching live execution spread metrics via market depth...")

        # Construct quotes payload using the discovered token
        instr = [{"instrument_token": str(token), "exchange_segment": segment}]
        
        # Pull market depth payload exactly like your working option block
        res = client.quotes(instrument_tokens=instr, quote_type="depth")

        if not res or not isinstance(res, list) or len(res) == 0:
            print(f"{Fore.RED}❌ Error: Empty or invalid depth response array.")
            return 0.0
        
        # Unwrap list array element
        data = res[0] 
        
        # Drill down into depth structures exactly like your working layout
        depth = data.get("depth", {})
        buy_list = depth.get("buy", [])
        sell_list = depth.get("sell", [])

        # Process the bid/ask spreads securely
        bid = float(buy_list[0].get("price", 0)) if buy_list else 0.0
        ask = float(sell_list[0].get("price", 0)) if sell_list else 0.0
        
        if bid > 0 and ask > 0:
            return round((bid + ask) / 2, 2)
        
        # Pure underlying fallback to LTP if depth blocks come up blank
        return float(data.get("last_price", 0))
        
    except Exception as e:
        print(f"{Fore.RED}❌ Execution Error inside pricing logic: {e}")
        return 0.0


def main():
    # 1. Initialize session using your verified runclntpxy client
    session = get_session()
    if not session:
        print(f"{Fore.RED}❌ Authentication Failed: Session could not be initialized.")
        return

    # 2. Get dynamic near-month symbol text (e.g., NIFTY26SEPFUT)
    target_symbol = get_current_month_future_symbol()

    # 3. Find token dynamically and pull mid-price using your working option routine
    live_price = find_and_get_mid_price(session, symbol_text=target_symbol)
    
    print(f"\n{Fore.YELLOW}========================================")
    print(f" 📊 NIFTY FUTURE LIVE PRICE: {Fore.GREEN}₹{live_price:,.2f}")
    print(f"{Fore.YELLOW}========================================\n")


if __name__ == "__main__":
    main()


