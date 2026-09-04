import json
import requests
from runclntpxy import get_session

def get_nifty_future_token_via_mirror():
    """
    Fetches the precise live NIFTY current-month future numeric token
    from a lightweight open-source daily mirror. Uses virtually 0MB RAM.
    """
    print("1. Resolving NIFTY Future Token ID via mirror stream...")
    
    # Using an open token database mirror to extract today's live mapping 
    # without hitting Kotak's blocked or high-RAM CSV endpoints.
    url = "https://githubusercontent.com"
    
    try:
        response = requests.get(url, timeout=10)
        if response.status_code != 200:
            print(f"Mirror failed with status code: {response.status_code}")
            return None
            
        instruments = response.json()
        future_contracts = []
        
        for item in instruments:
            # Check for NIFTY Index Futures
            if item.get('symbol') == 'NIFTY' and item.get('instrument_type') == 'FUTIDX':
                future_contracts.append(item)
                
        if not future_contracts:
            print("No matching NIFTY Future tokens found in raw file.")
            return None
            
        # Sort contracts by expiry to guarantee index 0 is the near current month
        future_contracts.sort(key=lambda x: x.get('expiry', ''))
        
        current_contract = future_contracts[0]
        return {
            "token": str(current_contract.get('instrument_token')),
            "trading_symbol": current_contract.get('trading_symbol')
        }
        
    except Exception as e:
        print(f"Mirror fetch failed: {e}")
        return None

def main():
    # 1. Grab the precise live numerical token ID
    contract_info = get_nifty_future_token_via_mirror()
    if not contract_info:
        print("Fallback: Please input the token manually.")
        return
        
    print(f"Target Matched -> {contract_info['trading_symbol']} | Token: {contract_info['token']}")

    # 2. Authenticate using your script
    session = get_session()
    if not session:
        return

    # 3. Request light OHLC values using Kotak Neo API
    try:
        print("2. Requesting live quote matrix...")
        instrument_payload = [
            {
                "instrument_token": contract_info['token'],
                "exchange_segment": "nse_fo"
            }
        ]
        
        quote_response = session.quotes(
            instrument_tokens=instrument_payload,
            quote_type="ohlc"
        )

        print("\n===== NIFTY FUTURE LATEST OHLC =====")
        print(json.dumps(quote_response, indent=4))

    except Exception as e:
        print(f"Kotak Quote Fetch Failed: {e}")

if __name__ == "__main__":
    main()


