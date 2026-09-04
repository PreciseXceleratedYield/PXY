import os
import pandas as pd
# Import your authenticated session function from runclntpxy.py
from runclntpxy import get_session 

def download_tokens_via_sdk_session():
    print("Initializing session via runclntpxy...")
    session = get_session()
    
    if not session:
        print("Error: Could not authenticate session. Check credentials.")
        return

    print("Session authenticated successfully! ✅")
    
    try:
        # 1. Borrow the pre-authenticated network session layer directly from the SDK
        # The NeoAPI wrapper handles token refreshes internally via session.client.session
        http_session = session.client.session
        
        # 2. Get environment configuration
        base_url = "https://api.kotakneo.com" if getattr(session, "environment", "prod") == "prod" else "https://kotak.com"
        file_paths_url = f"{base_url}/script-details/1.0/masterscrip/file-paths"
        
        print("Requesting master scrip URLs via authenticated SDK session...")
        
        # Hit the file path engine using Kotak SDK's verified internal networking
        response = http_session.get(file_paths_url)
        
        if response.status_code == 200:
            data = response.json()
            fno_file_url = None
            
            # Extract the target download link for NSE Futures & Options
            for item in data.get("data", []):
                if item.get("exchange") == "nse_fo":
                    fno_file_url = item.get("filePath")
                    break
                    
            if fno_file_url:
                print(f"File found! Downloading from: {fno_file_url}")
                
                # Fetch and pull down the CSV through the authenticated connection
                df = pd.read_csv(fno_file_url)
                
                # Clean up column header spacing properties
                df.columns = df.columns.str.strip()
                
                # Save the file straight into your local workspace directory
                output_filename = "kotak_neo_nse_fo_tokens.csv"
                df.to_csv(output_filename, index=False)
                
                print(f"\nSuccess! File written cleanly to local directory: '{output_filename}' 🚀")
                print("--- Data Preview ---")
                print(df[['pToken', 'pSymbol', 'pExpiryDate']].head(5))
            else:
                print("Could not find the 'nse_fo' exchange segment in Kotak's server listing.")
        else:
            print(f"Network Request Failed. Status: {response.status_code}, Msg: {response.text}")
            
    except Exception as e:
        print(f"An unexpected error occurred during processing: {e}")

if __name__ == "__main__":
    download_tokens_via_sdk_session()


