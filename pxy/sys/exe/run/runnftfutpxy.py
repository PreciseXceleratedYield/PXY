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
        
        # Corrected parameters using 'symbol' and filtering with option_type="FUT"
        raw_data = session.search_scrip(
            exchange_segment="nse_fo", 
            symbol="NIFTY",
            option_type="FUT"
        )
        
        if raw_data:
            df = pd.DataFrame(raw_data)
            
            # Clean up column header spacing
            df.columns = df.columns.str.strip()
            
            # Save the clean tokens list into your local folder
            output_file = "kotak_neo_nifty_futures.csv"
            df.to_csv(output_file, index=False)
            
            print(f"\nSuccess! Tokens written to: '{output_file}' 🚀")
            print("--- Found Active Nifty Futures ---")
            
            # Display important columns if they exist in the response
            display_cols = [c for c in ['pToken', 'pSymbol', 'pExpiryDate'] if c in df.columns]
            if display_cols:
                print(df[display_cols].to_string(index=False))
            else:
                print(df.head(10).to_string(index=False))
        else:
            print("The API executed but returned an empty list. Confirm that NIFTY contracts are active.")
            
    except Exception as e:
        print(f"An unexpected error occurred during API communication: {e}")

if __name__ == "__main__":
    fetch_futures_tokens_live()
