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
    
    # Define the instruments you want to find (e.g., Nifty or Bank Nifty Futures)
    search_symbol = "NIFTY" 
    
    try:
        print(f"Searching for active '{search_symbol}' instruments via SDK...")
        
        # The native SDK method 'search_scrip' runs completely through the API session,
        # avoiding local file-write limitations and local machine DNS issues.
        raw_data = session.search_scrip(
            exchange_segment="nse_fo", 
            search_string=search_symbol
        )
        
        if raw_data:
            # Structuring the returned list into a clean pandas data frame
            df = pd.DataFrame(raw_data)
            
            # Clean up column header spacing properties
            df.columns = df.columns.str.strip()
            
            # Filter specifically for Futures contracts (excluding Options)
            # Kotak symbols for futures usually end with 'FUT' or contain 'FUT'
            if 'pSymbol' in df.columns:
                futures_df = df[df['pSymbol'].str.contains('FUT', case=False, na=False)]
            else:
                futures_df = df
            
            # Save the clean filtered tokens straight into your folder
            output_file = f"kotak_neo_{search_symbol.lower()}_futures.csv"
            futures_df.to_csv(output_file, index=False)
            
            print(f"\nSuccess! Filtered tokens written to: '{output_file}' 🚀")
            print("--- Found Active Futures Instruments ---")
            
            # Show token numbers along with their matching expiry parameters
            display_cols = [c for c in ['pToken', 'pSymbol', 'pExpiryDate'] if c in futures_df.columns]
            print(futures_df[display_cols].head(10).to_string(index=False))
            
        else:
            print("The API executed successfully but returned an empty search index.")
            
    except Exception as e:
        print(f"An unexpected error occurred during API communication: {e}")

if __name__ == "__main__":
    fetch_futures_tokens_live()

