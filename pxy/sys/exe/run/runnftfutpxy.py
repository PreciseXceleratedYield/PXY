import json
from runclntpxy import get_session  # Change 'your_filename' to your actual script file name

import json
import pandas as pd

def get_nifty_current_future_ohlc():
    # 1. Initialize session
    session = get_session()
    
    if not session:
        print("Failed to initialize session.")
        return

    try:
        print("\n1. Fetching NIFTY Future instrument parameters...")
        
        # Correct arguments according to Kotak Neo SDK specs
        search_result = session.search_scrip(
            exchange_segment="nse_fo", 
            symbol="NIFTY"
        )
        
        # Check if response payload is valid
        if not search_result or 'data' not in search_result or not search_result['data']:
            print("Error: Empty data payload. Check your segment permissions or API status.")
            return

        # 2. Extract Index Futures (FUTIDX)
        # Note: Kotak Neo client maps raw API fields dynamically, so we safely check both potential casing types.
        future_contracts = []
        for item in search_result['data']:
            inst_type = item.get('instrument_type') or item.get('pInstType') or ""
            if inst_type.upper() == 'FUTIDX':
                future_contracts.append(item)

        if not future_contracts:
            print("Error: No active NIFTY Future contracts found in search array.")
            return

        # Kotak natively sorts closest contracts first. Index 0 is our Current Month.
        current_month_fut = future_contracts[0]
        
        # Support fallback variations for dictionary keys returned by search endpoint
        token = current_month_fut.get('instrument_token') or current_month_fut.get('pSymbolToken')
        trading_symbol = current_month_fut.get('trading_symbol') or current_month_fut.get('pTrdSymbol')
        exchange = current_month_fut.get('exchange_segment') or "nse_fo"
        
        if not token:
            print("Error: Could not extract Instrument Token ID from contract data.")
            return

        print(f"Targeting Contract: {trading_symbol} | Token ID: {token}")

        # 3. Pull Live Market OHLC Data 
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

