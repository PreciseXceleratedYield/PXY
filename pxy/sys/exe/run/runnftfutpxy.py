import json
from runclntpxy import get_session

def get_nifty_ohlc_instant():
    session = get_session()
    if not session:
        return

    try:
        print("Fetching live NIFTY Future OHLC directly via explicit token allocation...")
        
        # --- THE FIX ---
        # Instead of an empty numerical lookup token, we pass Kotak's active 
        # root index future designation directly into the engine segment payload array.
        instrument_payload = [
            {
                "instrument_token": "NIFTY-I",   # Kotak's official direct keyword for current near-month future
                "exchange_segment": "nse_fo"
            }
        ]
        
        # Pull only the required OHLC metrics block
        quote_response = session.quotes(
            instrument_tokens=instrument_payload,
            quote_type="ohlc"
        )

        print("\n===== NIFTY FUTURE LATEST OHLC =====")
        print(json.dumps(quote_response, indent=4))

    except Exception as e:
        print(f"API Execution Failure: {e}")

if __name__ == "__main__":
    get_nifty_ohlc_instant()


