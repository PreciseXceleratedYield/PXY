import json
import requests
from runclntpxy import get_session

def get_current_nifty_future_token():
    """
    Directly queries Kotak Neo's lightweight daily JSON master dictionary 
    to extract the active dynamic NIFTY Future numerical token.
    Uses almost 0MB RAM.
    """
    print("1. Resolving current month NIFTY Future Token ID dynamically...")
    
    # Kotak's light public endpoint for dynamic instrument mapping search
    url = "https://kotaksecurities.com"
    
    try:
        # Requesting data with a clean timeout
        response = requests.get(url, timeout=10)
        if response.status_code != 200:
            print("Failed to access Kotak's public token registry.")
            return None
            
        master_data = response.json()
        
        future_contracts = []
        for item in master_data:
            symbol = item.get('symbol', '').upper()
            inst_type = item.get('instrument_type', '').upper() or item.get('pInstType', '').upper()
            
            # Filter specifically for NIFTY Index Futures
            if symbol == 'NIFTY' and inst_type == 'FUTIDX':
                future_contracts.append(item)
                
        if not future_contracts:
            print("Could not locate NIFTY Future entries inside registry.")
            return None
            
        # Sort by expiry to ensure index 0 is always the closest current near-month contract
        future_contracts.sort(key=lambda x: x.get('expiry', ''))
        
        current_month = future_contracts[0]
        return {
            "token": str(current_month.get('instrument_token') or current_month.get('pSymbolToken')),
            "trading_symbol": current_month.get('trading_symbol') or current_month.get('pTrdSymbol')
        }
    except Exception as e:
        print(f"Token Resolution Helper crashed: {e}")
        return None

def main():
    # Fetch exact true current month numerical token
    contract_info = get_current_nifty_future_token()
    if not contract_info or not contract_info['token']:
        print("Aborting: Valid numerical neosymbol token could not be fetched.")
        return
        
    print(f"Target Acquired -> {contract_info['trading_symbol']} (Token ID: {contract_info['token']})")

    # 2. Authenticate session
    session = get_session()
    if not session:
        return

    try:
        print("2. Fetching live market OHLC data metrics...")
        
        # Build payload with verified straight numbers
        instrument_payload = [
            {
                "instrument_token": contract_info['token'],  # Numeric token (e.g. "45920")
                "exchange_segment": "nse_fo"
            }
        ]
        
        # Requesting quotes
        quote_response = session.quotes(
            instrument_tokens=instrument_payload,
            quote_type="ohlc"
        )

        print("\n===== NIFTY FUTURE LATEST OHLC =====")
        print(json.dumps(quote_response, indent=4))

    except Exception as e:
        print(f"API Execution Failure during quoting: {e}")

if __name__ == "__main__":
    main()


