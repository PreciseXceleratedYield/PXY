def get_nifty_future_ohlc_direct():
    # 1. Initialize your session
    session = get_session()
    if not session:
        return

    try:
        print("\n1. Resolving NIFTY Future token via lightweight search bypass...")
        
        # We query Kotak's light quote finder with the explicit symbol name format.
        # This completely skips downloading the huge master file database.
        search_payload = session.search_scrip(exchange_segment="nse_fo", symbol="NIFTY")
        
        if not search_payload or 'data' not in search_payload:
            # Fallback hardcoded lookups if your client setup strips parameters
            print("Trying fallback token broadcast query...")
            # Kotak Neo allows direct searching using the trading symbol text array
            search_payload = session.search_scrip(exchange_segment="nse_fo", symbol="NIFTY-I")

        # 2. Extract the contract safely without heavy processing loops
        contracts = search_payload.get('data', [])
        target_contract = None
        
        for contract in contracts:
            inst_type = (contract.get('instrument_type') or contract.get('pInstType') or '').upper()
            # FUTIDX ensures we pick index futures, index 0 is always the current month near contract
            if inst_type == 'FUTIDX':
                target_contract = contract
                break

        if not target_contract:
            print("Error: Could not isolate NIFTY Future contract array.")
            return

        token = target_contract.get('instrument_token') or target_contract.get('pSymbolToken')
        trading_symbol = target_contract.get('trading_symbol') or target_contract.get('pTrdSymbol')
        
        print(f"Target Acquired -> {trading_symbol} (Token: {token})")

        # 3. Pull exactly the latest OHLC matrix data block
        print("2. Fetching live OHLC data metrics...")
        instrument_payload = [
            {
                "instrument_token": str(token),
                "exchange_segment": "nse_fo"
            }
        ]
        
        quote_response = session.quotes(
            instrument_tokens=instrument_payload, 
            quote_type="ohlc"
        )
        
        # 4. Print clean JSON terminal output
        print("\n===== NIFTY FUTURE OHLC RESULTS =====")
        print(json.dumps(quote_response, indent=4))

    except Exception as e:
        print(f"Execution Error: {e}")

if __name__ == "__main__":
    get_nifty_future_ohlc_direct()
