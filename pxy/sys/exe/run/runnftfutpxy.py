import json
from runclntpxy import get_session

# !!! CHANGE THIS VALUE EVERY MONTH AFTER EXPIRES !!!
# Look up the current active NIFTY Future token from your Kotak portal 
# or via an online Neo master file viewer.
NIFTY_CURRENT_FUTURE_TOKEN = "35012"  # Example Token ID for NIFTY Futures

def get_nifty_ohlc_direct():
    session = get_session()
    if not session:
        return

    try:
        print(f"Fetching live OHLC using straight token ID: {NIFTY_CURRENT_FUTURE_TOKEN}")
        
        # Build the exact, lightweight instrument payload using the hardcoded token
        instrument_payload = [
            {
                "instrument_token": str(NIFTY_CURRENT_FUTURE_TOKEN),
                "exchange_segment": "nse_fo"
            }
        ]
        
        # Fetch the live quote
        quote_response = session.quotes(
            instrument_tokens=instrument_payload,
            quote_type="ohlc"
        )

        print("\n===== NIFTY FUTURE LATEST OHLC =====")
        print(json.dumps(quote_response, indent=4))

    except Exception as e:
        print(f"API Execution Failure: {e}")

if __name__ == "__main__":
    get_nifty_ohlc_direct()

