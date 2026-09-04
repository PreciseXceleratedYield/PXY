import json
from runclntpxy import get_session

def get_nifty_future_quote():
    # 1. Initialize session cleanly from your client file
    session = get_session()
    if not session:
        print("Failed to initialize session.")
        return

    try:
        print("Requesting latest market quote block for NIFTY near-month future...")
        
        # We pass Kotak's exact native string identification token arrangement 
        # directly into the quote collection array payload
        instrument_payload = [
            {
                "instrument_token": "NIFTY-I",   # 'NIFTY-I' maps straight to the current month futures contract
                "exchange_segment": "nse_fo"
            }
        ]
        
        # Requesting the full 'all' payload so you can confirm the exact symbol string name
        quote_response = session.quotes(
            instrument_tokens=instrument_payload,
            quote_type="all"
        )

        print("\n===== NIFTY CURRENT FUTURE FULL QUOTE =====")
        print(json.dumps(quote_response, indent=4))

    except Exception as e:
        print(f"API Execution Failure: {e}")

if __name__ == "__main__":
    get_nifty_future_quote()

