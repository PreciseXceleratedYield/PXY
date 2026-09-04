from datetime import datetime
import calendar
import json
# Import your authenticated session function from runclntpxy.py
from runclntpxy import get_session 

def get_current_month_expiry_date():
    """
    Calculates the exact last Tuesday date string for the current month 
    matching Kotak's F&O string layout (e.g., '29SEP26').
    """
    today = datetime.today()
    year = today.year
    month = today.month
    
    # Generate calendar framework for the current month
    month_cal = calendar.monthcalendar(year, month)
    
    # Extract the last week that has a Tuesday (Index 1 = Tuesday)
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
        # Build the exact request structure required by the SDK documentation
        instrument_payload = [
            {
                "exchange_segment": "nse_fo",
                "symbol": target_symbol
            }
        ]
        
        print("Requesting quote matrix from Kotak engine...")
        quote_response = session.quotes(instrument_tokens=instrument_payload)
        
        # Parse output data
        if quote_response:
            # Handle if the SDK returns data wrapped inside a 'data' key or a direct list/dict
            data_block = quote_response.get("data", quote_response) if isinstance(quote_response, dict) else quote_response
            
            # If the response comes back as a list, unpack the first entry
            if isinstance(data_block, list) and len(data_block) > 0:
                data_block = data_block[0]
                
            # Extract key variables directly
            token = data_block.get('tok') or data_block.get('pToken') or data_block.get('instrument_token')
            ltp = data_block.get('ltp') or data_block.get('pLastTradedPrice') or data_block.get('last_price')
            trading_symbol = data_block.get('tsym') or data_block.get('pSymbol') or data_block.get('symbol')
            
            print("\n==============================")
            print(f"  DETECTED : {trading_symbol if trading_symbol else target_symbol}")
            print(f"  TOKEN    : {token}")
            print(f"  LIVE LTP : ₹ {ltp}")
            print("==============================")
        else:
            print(f"\n❌ Server returned an empty response. Response payload: {quote_response}")
            
    except Exception as e:
        print(f"API Connection Exception: {e}")

if __name__ == "__main__":
    autodetect_and_get_quotes()

