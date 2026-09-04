import json
from runclntpxy import get_session
from colorama import Fore, Style, init

init(autoreset=True)

def get_this_month_future_price_fixed():
    # 1. Initialize session using runclntpxy
    session = get_session()
    if not session:
        print(f"{Fore.RED}❌ Authentication Failed.")
        return

    try:
        print("🔍 Querying server passing ALL explicit values for this month's Future...")

        # PASSING ALL VALUES: This forces Kotak to return ONLY 1 ROW.
        # For September 2026, the expiry string format is "24SEP2026"
        search_result = session.search_scrip(
            exchange_segment="nse_fo", 
            symbol="NIFTY",
            expiry="24SEP2026",
            option_type="X",       # "X" or blank "" signals Stock/Index Futures to Kotak's backend
            strike_price="0"       # Futures don't have a strike price, so pass "0" or "0.00"
        )
        
        if not search_result or 'data' not in search_result or len(search_result['data']) == 0:
            print(f"{Fore.RED}❌ No rows returned. Trying fallback parameters...")
            # Fallback wrapper if your specific SDK version expects blank options strings
            search_result = session.search_scrip(
                exchange_segment="nse_fo", 
                symbol="NIFTY",
                expiry="24SEP2026",
                option_type="",
                strike_price=""
            )

        if not search_result or 'data' not in search_result or len(search_result['data']) == 0:
            print(f"{Fore.RED}❌ Error: Could not fetch contract row.")
            return

        # Process the single row safely from the list array
        scrip_data = search_result['data'][0] if isinstance(search_result['data'], list) else search_result['data']
        token = scrip_data.get("instrument_token") or scrip_data.get("pSymbolToken")
        trading_symbol = scrip_data.get("trading_symbol") or scrip_data.get("pTrdSymbol")
        
        print(f"🎯 Target Locked -> Name: {Fore.GREEN}{trading_symbol} {Fore.WHITE}| Token: {Fore.GREEN}{token}")

        # 2. Fetch the market depth price using your verified configuration layout
        instr = [{"instrument_token": str(token), "exchange_segment": "nse_fo"}]
        res = session.quotes(instrument_tokens=instr, quote_type="depth")

        if not res or not isinstance(res, list) or len(res) == 0:
            print(f"{Fore.RED}❌ Empty price response.")
            return
        
        data = res[0]
        depth = data.get("depth", {})
        buy_list = depth.get("buy", [])
        sell_list = depth.get("sell", [])

        # Process mid-price spread calculations from your working code structure
        bid = float(buy_list[0].get("price", 0)) if buy_list else 0.0
        ask = float(sell_list[0].get("price", 0)) if sell_list else 0.0
        
        if bid > 0 and ask > 0:
            mid_price = round((bid + ask) / 2, 2)
        else:
            mid_price = float(data.get("last_price", 0))

        print(f"\n{Fore.YELLOW}========================================")
        print(f" 📊 NIFTY FUT LIVE PRICE: {Fore.GREEN}₹{mid_price:,.2f}")
        print(f"{Fore.YELLOW}========================================\n")

    except Exception as e:
        print(f"{Fore.RED}❌ Engine Failure: {e}")

if __name__ == "__main__":
    get_this_month_future_price_fixed()


