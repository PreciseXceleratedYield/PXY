import json
import requests
import csv
from datetime import datetime
from runclntpxy import get_session

def get_nifty_future_token_low_ram():
    """
    Streams Kotak's contract master line-by-line to extract the 
    current month NIFTY Future token using almost zero RAM.
    """
    # Generate today's URL format dynamically
    today_str = datetime.now().strftime("%Y-%m-%d")
    url = f"https://kotaksecurities.com{today_str}/transformed/nse_fo.csv"
    
    try:
        # stream=True processes rows one by one without caching the 100MB file into memory
        response = requests.get(url, stream=True, timeout=10)
        if response.status_code != 200:
            return None

        lines = (line.decode('utf-8') for line in response.iter_lines())
        reader = csv.DictReader(lines)
        
        future_contracts = []
        for row in reader:
            row_clean = {k.lower(): v for k, v in row.items()}
            symbol = row_clean.get('symbol', '').upper()
            inst_type = row_clean.get('instrument_type', '').upper() or row_clean.get('pinsttype', '').upper()
            
            if symbol == 'NIFTY' and inst_type == 'FUTIDX':
                future_contracts.append(row_clean)

        if not future_contracts:
            return None

        # Sort contracts by expiry to safely lock index 0 as the nearest current month contract
        expiry_key = 'expiry' if 'expiry' in future_contracts else 'pexpirydate'
        try:
            future_contracts.sort(key=lambda x: x.get(expiry_key, ''))
        except Exception:
            pass

        current_month_fut = future_contracts
        return {
            "token": current_month_fut.get('instrument_token') or current_month_fut.get('psymboltoken'),
            "trading_symbol": current_month_fut.get('trading_symbol') or current_month_fut.get('pbyline_age')
        }
    except Exception:
        return None

def main():
    # 1. Fetch token via lightweight stream lookup
    contract_info = get_nifty_future_token_low_ram()
    if not contract_info or not contract_info['token']:
        print("Error: Could not retrieve NIFTY Future instrument parameters dynamically.")
        return

    print(f"Targeting: {contract_info['trading_symbol']} | Token: {contract_info['token']}")

    # 2. Initialize Kotak Neo Client from runclntpxy
    session = get_session()
    if not session:
        return

    try:
        # 3. Pull the clean, ultra-light OHLC metrics
        instrument_payload = [
            {
                "instrument_token": str(contract_info['token']),
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
        print(f"API Execution Failure: {e}")

if __name__ == "__main__":
    main()
