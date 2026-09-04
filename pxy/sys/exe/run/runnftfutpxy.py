import json
from runclntpxy import get_session  # Change 'your_filename' to your actual script file name

import json
import pandas as pd
def get_just_ohlc():
    session = get_session()
    if not session:
        return

    try:
        # 1. Look up the light quote configuration directly
        # Instead of scanning the entire master database, we pull search hits directly 
        # using the modern keyword arguments layout.
        search_result = session.search_scrip(exchange_segment="nse_fo", symbol="NIFTY")
        
        if not search_result or 'data' not in search_result:
            print("Could not retrieve market data payload.")
            return
            
        # Isolate the current near-month index future contract (FUTIDX)
        future_contracts = [
            item for item in search_result['data'] 
            if (item.get('instrument_type') or item.get('pInstType', '')).upper() == 'FUTIDX'
        ]
        
        if not future_contracts:
            print("No active NIFTY Future contracts available right now.")
            return
            
        # Extract the closest expiring contract token
        target_contract = future_contracts[0]
        token = target_contract.get('instrument_token') or target_contract.get('pSymbolToken')
        trading_symbol = target_contract.get('trading_symbol') or target_contract.get('pTrdSymbol')
        
        print(f"Fetching Live Data for: {trading_symbol} (ID: {token})")
        
        # 2. Extract exactly the OHLC data matrix
        instrument_payload = [{"instrument_token": str(token), "exchange_segment": "nse_fo"}]
        quote_response = session.quotes(instrument_tokens=instrument_payload, quote_type="ohlc")
        
        # 3. Clean Print the Output
        print("\n===== NIFTY FUTURE LATEST OHLC =====")
        print(json.dumps(quote_response, indent=4))
        
    except Exception as e:
        print(f"Error fetching OHLC values: {e}")

if __name__ == "__main__":
    get_just_ohlc()
