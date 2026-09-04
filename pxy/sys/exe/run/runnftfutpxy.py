import re
from datetime import datetime
import calendar
from colorama import Fore, Style, init
# Import your authenticated session function from runclntpxy.py
from runclntpxy import get_session 

init(autoreset=True)

def get_current_month_expiry_date():
    """
    Calculates the exact last Tuesday day integer for the current month
    and formats it to match Kotak's F&O string layout (e.g., '29SEP26').
    """
    today = datetime.today()
    year = today.year
    month = today.month
    
    # Generate calendar framework for the current month (list of weekly integer arrays)
    month_cal = calendar.monthcalendar(year, month)
    
    # Identify the last week list containing a valid Tuesday (Index 1)
    if month_cal[-1][1] != 0:
        last_tuesday_day = month_cal[-1][1]
    else:
        last_tuesday_day = month_cal[-2][1]
        
    expiry_date_str = f"{last_tuesday_day:02d}{today.strftime('%b').upper()}{str(year)[2:]}"
    return expiry_date_str

def autodetect_and_get_quotes():
    print("Initializing session via runclntpxy...")
    session = get_session()
    
    if not session:
        print(f"{Fore.RED}Error: Authentication failed.")
        return

    print("Session authenticated successfully! ✅")
    
    # 1. Dynamically compute the contract string format
    detected_expiry = get_current_month_expiry_date()
    target_symbol = f"Nifty 50 Futures {detected_expiry}"
    
    print(f"Auto-detected current month symbol syntax: '{target_symbol}'")
    
    # 2. Query Kotak Neo's quotes system using the primary documentation layout
    try:
        instrument_payload = [
            {
                "instrument_token": target_symbol,
                "exchange_segment": "nse_fo"
            }
        ]
        
        print("Requesting quote matrix from Kotak engine...")
        quote_response = session.quotes(instrument_tokens=instrument_payload)
        
        # Initialize token and price variables
        token, ltp, trading_symbol = None, None, None
        
        if quote_response:
            # Standardize different market return variants (dict vs list layers)
            data_list = quote_response.get("data") if isinstance(quote_response, dict) else quote_response
            if isinstance(data_list, dict):
                data_list = [data_list]
                
            if isinstance(data_list, list) and len(data_list) > 0:
                instrument_data = data_list[0]
                token = instrument_data.get('tok') or instrument_data.get('pToken') or instrument_data.get('instrument_token')
                ltp = instrument_data.get('ltp') or instrument_data.get('pLastTradedPrice') or instrument_data.get('last_price')
                trading_symbol = instrument_data.get('tsym') or instrument_data.get('pSymbol') or instrument_data.get('symbol')

        # 3. Fallback Layer: If snapshot fields return None, request an explicit scrip verification link
        if not ltp or str(ltp).lower() == 'none' or not token:
            print("Snapshot value missing. Executing alternate data extraction matrix...")
            
            # Use 'NIFTY' loop variant to pull the direct active contract mappings
            search_res = session.search_scrip(exchange_segment="nse_fo", symbol="NIFTY")
            
            if search_res:
                search_data = search_res.get("data", search_res) if isinstance(search_res, dict) else search_res
                if isinstance(search_data, dict):
                    search_data = [search_data]
                    
                if isinstance(search_data, list):
                    for item in search_data:
                        symbol_name = str(item.get('pSymbol') or item.get('tsym') or '').upper()
                        # Match current month string format (e.g. '29SEP26') and isolate FUT records
                        if detected_expiry in symbol_name and 'FUT' in symbol_name:
                            token = item.get('pToken') or item.get('tok')
                            trading_symbol = item.get('pSymbol') or item.get('tsym')
                            
                            # Fetch the actual live quote using the true numeric token found
                            numeric_payload = [{"instrument_token": str(token), "exchange_segment": "nse_fo"}]
                            fresh_quote = session.quotes(instrument_tokens=numeric_payload)
                            
                            fresh_data = fresh_quote.get("data", fresh_quote) if isinstance(fresh_quote, dict) else fresh_quote
                            if isinstance(fresh_data, list) and len(fresh_data) > 0:
                                fresh_data = fresh_data[0]
                            elif isinstance(fresh_data, dict) and "data" in fresh_data:
                                if isinstance(fresh_data["data"], list) and len(fresh_data["data"]) > 0:
                                    fresh_data = fresh_data["data"][0]
                                    
                            ltp = fresh_data.get('ltp') or fresh_data.get('last_price') or fresh_data.get('pLastTradedPrice')
                            break

        # 4. Display Results
        print("\n==============================")
        print(f"  SYMBOL : {trading_symbol if trading_symbol else target_symbol}")
        print(f"  TOKEN  : {token}")
        print(f"  LTP    : ₹ {ltp}")
        print("==============================")
            
    except Exception as e:
        print(f"API Connection Exception: {e}")

if __name__ == "__main__":
    autodetect_and_get_quotes()
