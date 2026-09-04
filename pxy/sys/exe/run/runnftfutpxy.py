import json
from runclntpxy import get_session  # Change 'your_filename' to your actual script file name

import json
import pandas as pd


def get_nifty_future_ohlc():
    session = get_session()
    if not session:
        print("Failed to initialize session.")
        return

    try:
        print("\n1. Fetching Scrip Master file for NSE F&O...")
        
        # Pull the complete live scrip file for futures & options directly
        # This returns a temporary local CSV path or direct dataframe download
        scrip_file_info = session.scrip_master(exchange_segment="nse_fo")
        
        if not scrip_file_info or 'file_path' not in scrip_file_info:
            print("Fallback: Attempting direct text-based scrip search...")
            # If scrip master fails, retry search_scrip using the correct 'search_text' parameter
            search_result = session.search_scrip(exchange_segment="nse_fo", search_text="NIFTY")
            if not search_result or 'data' not in search_result:
                print("Error: Search engine returned empty data payload.")
                return
            contracts_df = pd.DataFrame(search_result['data'])
        else:
            # Read Kotak's official scrip master CSV file
            contracts_df = pd.read_csv(scrip_file_info['file_path'])

        # 2. Strict Filter: Extract only NIFTY Index Futures (FUTIDX)
        # Columns in scrip master usually use lowercase keys or mapped names
        # We ensure casing compatibility for 'pSymbol' / 'symbol' and 'pInstType' / 'instrument_type'
        contracts_df.columns = contracts_df.columns.str.lower()
        
        future_contracts = contracts_df[
            (contracts_df['symbol'].str.upper() == 'NIFTY') & 
            (contracts_df['instrument_type'] == 'FUTIDX')
        ].copy()

        if future_contracts.empty:
            print("Error: No active NIFTY Future contracts located in file.")
            return

        # Sort by expiry date to ensure index 0 is always the closest current month expiry
        # If 'expiry_date' exists as a unix timestamp or text string, we sort it ascending
        if 'expiry' in future_contracts.columns:
            future_contracts = future_contracts.sort_values(by='expiry')

        # Select the nearest active current month future contract
        current_month_fut = future_contracts.iloc[0]
        token = current_month_fut['instrument_token']
        trading_symbol = current_month_fut['trading_symbol']
        exchange = "nse_fo"
        
        print(f"Targeting: {trading_symbol} | Token ID: {token}")

        # 3. Requesting Live OHLC Market Payload
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

        print("\n===== NIFTY FUTURE OHLC RESULTS =====")
        print(json.dumps(quote_response, indent=4))

    except Exception as e:
        print(f"API Execution Failure: {e}")

if __name__ == "__main__":
    get_nifty_future_ohlc()

