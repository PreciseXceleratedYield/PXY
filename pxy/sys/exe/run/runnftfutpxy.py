import json
from runclntpxy import get_session  # Change 'your_filename' to your actual script file name

def get_nifty_current_future_ohlc():
    # 1. Initialize your authenticated session
    session = get_session()
    
    if not session:
        print("Failed to initialize session.")
        return

    try:
        print("\n1. Fetching NIFTY Future instrument parameters...")
        # Querying the NSE F&O segment for NIFTY
        search_result = session.search_scrip(
            exchange_segment="nse_fo", 
            symbol="NIFTY"
        )
        
        if not search_result or 'data' not in search_result:
            print("Error: No data payload received from the search endpoint.")
            return

        # 2. Strict Filter: Isolate Index Futures (FUTIDX)
        # Kotak Neo automatically ranks the closest expiries first in this array
        future_contracts = [
            item for item in search_result['data'] 
            if item.get('instrument_type') == 'FUTIDX'
        ]

        if not future_contracts:
            print("Error: No NIFTY Future contracts found.")
            return

        # Select index [0] to dynamically lock the nearest (Current Month) expiry contract
        current_month_fut = future_contracts[0]
        token = current_month_fut['instrument_token']
        trading_symbol = current_month_fut['trading_symbol']
        exchange = current_month_fut['exchange_segment']
        
        print(f"Targeting: {trading_symbol} | Token ID: {token}")

        # 3. Pull OHLC Data 
        instrument_payload = [
            {
                "instrument_token": str(token),
                "exchange_segment": exchange
            }
        ]
        
        quote_response = session.quotes(
            instrument_tokens=instrument_payload,
            quote_type="ohlc"
        )

        # 4. Display Results
        print("\n===== NIFTY FUTURE OHLC RESULTS =====")
        print(json.dumps(quote_response, indent=4))

    except Exception as e:
        print(f"API Execution Failure: {e}")

if __name__ == "__main__":
    get_nifty_current_future_ohlc()
