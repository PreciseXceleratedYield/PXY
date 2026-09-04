from datetime import datetime
import calendar
import pandas as pd
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
        
    # Format to match Kotak's text engine syntax: e.g., '29SEP26'
    expiry_date_str = f"{last_tuesday_day:02d}{today.strftime('%b').upper()}{str(year)[2:]}"
    return expiry_date_str

def autodetect_and_quote():
    print("Initializing session via runclntpxy...")
    session = get_session()
    
    if not session:
        print("Error: Authentication failed.")
        return

    print("Session authenticated successfully! ✅")
    
    # 1. Dynamically compute the contract format suffix
    detected_expiry = get_current_month_expiry_date()
    target_symbol = f"Nifty 50 Futures {detected_expiry}"
    
    print(f"Auto-detected current month symbol syntax: '{target_symbol}'")
    
    # 2. Call the active quote engine
    try:
        quote_response = session.quote(
            exchange_segment="nse_fo",
            symbol=target_symbol
        )
        
        if quote_response and 'data' in quote_response:
            data = quote_response['data']
            
            token = data.get('tok') or data.get('pToken')
            ltp = data.get('ltp') or data.get('pLastTradedPrice')
            trading_symbol = data.get('tsym') or data.get('pSymbol')
            
            print("\n==============================")
            print(f"  DETECTED : {trading_symbol}")
            print(f"  TOKEN    : {token}")
            print(f"  LIVE LTP : ₹ {ltp}")
            print("==============================")
        else:
            print(f"\n❌ Could not pull quote metrics. Response: {quote_response}")
            
    except Exception as e:
        print(f"API Connection Exception: {e}")

if __name__ == "__main__":
    autodetect_and_quote()
