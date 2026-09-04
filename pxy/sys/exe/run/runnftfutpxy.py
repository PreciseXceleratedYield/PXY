import json
import time
from runclntpxy import get_session

def get_nifty_future_live_price():
    print("Initializing API session connection...")
    
    # Attempting connection via your client framework
    try:
        session = get_session()
    except Exception as auth_err:
        print(f"Critically blocked by Kotak's Authentication Gateway: {auth_err}")
        print("💡 Solution: Change your network IP (restart router) or verify your API keys are still active on the Neo Portal.")
        return

    if not session:
        print("Session authentication returned empty object due to connection drop.")
        return

    # Hardcode this month's exact, true current numerical token to completely bypass search engines
    # Replace this string token ID with the exact dynamic numeric ID active for the current month.
    NIFTY_LIVE_TOKEN = "35011" 

    try:
        print(f"Requesting LTP payload for Token ID: {NIFTY_LIVE_TOKEN}...")
        
        instrument_payload = [
            {
                "instrument_token": str(NIFTY_LIVE_TOKEN),
                "exchange_segment": "nse_fo"
            }
        ]
        
        # 'ltp' payload request returns only the live price text block instantly
        quote_response = session.quotes(
            instrument_tokens=instrument_payload,
            quote_type="ltp"
        )

        print("\n===== NIFTY FUTURE LIVE PRICE =====")
        print(json.dumps(quote_response, indent=4))

    except Exception as e:
        print(f"Live Price API Pipeline Error: {e}")

if __name__ == "__main__":
    get_nifty_future_live_price()



