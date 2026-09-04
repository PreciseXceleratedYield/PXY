from datetime import datetime
import calendar
# Import your authenticated session function from runclntpxy.py
from runclntpxy import get_session 

def get_current_month_expiry_date():
    """
    Calculates the exact last Tuesday day integer for the current month
    and formats it to match Kotak's F&O string layout (e.g., '29SEP26').
    """
    today = datetime.today()
    year = today.year
    month = today.month
    
    # Generate calendar framework for the current month (list of weekly lists)
    month_cal = calendar.monthcalendar(year, month)
    
    # Tuesday is index 1 in calendar.monthcalendar (0=Mon, 1=Tue, ..., 6=Sun)
    # Start from the last week of the month and look for a non-zero Tuesday
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
        print("Error: Authentication failed.")
        return

    print("Session authenticated successfully! ✅")
    
    # 1. Dynamically compute the contract string format
    detected_expiry = get_current_month_expiry_date()
    target_symbol = f"Nifty 50 Futures {detected_expiry}"
    
    print(f"Auto-detected current month symbol syntax: '{target_symbol}'")
    
    # 2. Call the official Kotak Neo v2 '.quotes()' endpoint method
    try:
        instrument_payload = [
            {
                "instrument_token": target_symbol,
                "exchange_segment": "nse_fo"
            }
        ]
        
        print("Requesting quote matrix from Kotak engine...")
        quote_response = session.quotes(instrument_tokens=instrument_payload)
        
        if quote_response:
            data_list = []
            if isinstance(quote_response, dict):
                data_list = quote_response.get("data", [])
                if not data_list and "message" not in quote_response:
                    data_list = [quote_response]
            elif isinstance(quote_response, list):
                data_list = quote_response

            if data_list and len(data_list) > 0:
                instrument_data = data_list[0]
                
                # Retrieve variable parameters safely
                token = instrument_data.get('tok') or instrument_data.get('pToken') or instrument_data.get('instrument_token')
                ltp = instrument_data.get('ltp') or instrument_data.get('pLastTradedPrice') or instrument_data.get('last_price')
                trading_symbol = instrument_data.get('tsym') or instrument_data.get('pSymbol') or instrument_data.get('symbol')
                
                print("\n==============================")
                print(f"  SYMBOL : {trading_symbol if trading_symbol else target_symbol}")
                print(f"  TOKEN  : {token}")
                print(f"  LTP    : ₹ {ltp}")
                print("==============================")
            else:
                print(f"\n❌ Response format parsed empty or returned an error block.")
                print(f"Server Payload: {quote_response}")
        else:
            print("\n❌ Server returned a completely empty response framework.")
            
    except Exception as e:
        print(f"API Connection Exception: {e}")

if __name__ == "__main__":
    autodetect_and_get_quotes()
