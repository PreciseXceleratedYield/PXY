import pandas as pd
# Import your authenticated session function from runclntpxy.py
from runclntpxy import get_session 

def fetch_futures_tokens_live():
    print("Initializing session via runclntpxy...")
    session = get_session()
    
    if not session:
        print("Error: Could not authenticate session. Check credentials.")
        return

    print("Session authenticated successfully! ✅")
    
    # List of common text query formats Kotak accepts for Futures
    search_variations = ["NIFTY-FUT", "NIFTY FUT", "NIFTY"]
    raw_data = None
    
    for variant in search_variations:
        try:
            print(f"Searching for active instruments using string: '{variant}'...")
            res = session.search_scrip(
                exchange_segment="nse_fo", 
                symbol=variant,
                option_type="FUT"
            )
            
            # Verify if the response contains actual data records rather than an error message
            if res and isinstance(res, dict) and "message" not in res:
                raw_data = res
                print(f"Success found matching records with variation: '{variant}'!")
                break
            elif res and isinstance(res, list):
                raw_data = res
                print(f"Success found matching records with variation: '{variant}'!")
                break
        except Exception as search_err:
            continue

    if not raw_data:
        # Fallback loop: Attempt search without the option_type constraint 
        print("Retrying broad index search variations without strict option_type filter...")
        for variant in ["NIFTY-FUT", "NIFTY FUT"]:
            try:
                res = session.search_scrip(exchange_segment="nse_fo", symbol=variant)
                if res and isinstance(res, (dict, list)) and "message" not in str(res):
                    raw_data = res
                    break
            except:
                continue

    if raw_data:
        try:
            # Normalize dictionary vs list formats safely
            if isinstance(raw_data, dict):
                if "data" in raw_data:
                    data_payload = raw_data["data"]
                    df = pd.DataFrame([data_payload] if isinstance(data_payload, dict) else data_payload)
                else:
                    df = pd.DataFrame([raw_data])
            else:
                df = pd.DataFrame(raw_data)
                
            # Strip trailing invisible spaces from headers
            df.columns = df.columns.str.strip()
            
            # Save the clean tokens list into your local folder
            output_file = "kotak_neo_nifty_futures.csv"
            df.to_csv(output_file, index=False)
            
            print(f"\nSuccess! Tokens written to: '{output_file}' 🚀")
            print("--- Found Active Nifty Futures ---")
            
            # Dynamic output layout display tracking
            display_cols = [c for c in ['pToken', 'pSymbol', 'pExpiryDate', 'tok', 'tsym', 'exp'] if c in df.columns]
            if display_cols:
                print(df[display_cols].to_string(index=False))
            else:
                print(df.head(10).to_string(index=False))
                
        except Exception as parse_err:
            print(f"Error compiling response dataframe: {parse_err}")
    else:
        print("\n❌ The API executed but all variant combinations returned no data records.")
        print("Verify your account segment authorizations for NSE F&O inside your Kotak App.")

if __name__ == "__main__":
    fetch_futures_tokens_live()
