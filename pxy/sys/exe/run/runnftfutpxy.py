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
    
    try:
        print("Searching for active NIFTY Futures instruments via SDK...")
        
        # Pull the scrip search mapping dictionary directly from Kotak API 
        raw_data = session.search_scrip(
            exchange_segment="nse_fo", 
            symbol="NIFTY",
            option_type="FUT"
        )
        
        if raw_data:
            # Print a quick diagnostic trace to see exactly what Kotak returned
            print(f"DEBUG - Raw Data Type: {type(raw_data)}")
            
            # Safe parsing logic: Force dictionary types into a list shell
            if isinstance(raw_data, dict):
                # If it's a nested dictionary with a 'data' key, target that array list
                if "data" in raw_data:
                    data_payload = raw_data["data"]
                    if isinstance(data_payload, dict):
                        df = pd.DataFrame([data_payload])
                    else:
                        df = pd.DataFrame(data_payload)
                else:
                    df = pd.DataFrame([raw_data])
            elif isinstance(raw_data, list):
                df = pd.DataFrame(raw_data)
            else:
                print(f"Unknown data structure returned: {raw_data}")
                return
            
            # Clean up column header spacing properties
            df.columns = df.columns.str.strip()
            
            # Save the clean tokens list into your local folder
            output_file = "kotak_neo_nifty_futures.csv"
            df.to_csv(output_file, index=False)
            
            print(f"\nSuccess! Tokens written to: '{output_file}' 🚀")
            print("--- Found Active Nifty Futures ---")
            
            # Display target tracking metrics cleanly
            display_cols = [c for c in ['pToken', 'pSymbol', 'pExpiryDate', 'tok', 'tsym', 'exp'] if c in df.columns]
            if display_cols:
                print(df[display_cols].to_string(index=False))
            else:
                print(df.head(10).to_string(index=False))
        else:
            print("The API executed but returned an empty list or None.")
            
    except Exception as e:
        print(f"An unexpected error occurred during API communication: {e}")

if __name__ == "__main__":
    fetch_futures_tokens_live()
