import os
import requests
import pandas as pd
# Import your authenticated session function from runclntpxy.py
from runclntpxy import get_session 

def download_futures_tokens_direct():
    print("Initializing session via runclntpxy...")
    session = get_session()
    
    if not session:
        print("Error: Could not authenticate session. Check credentials.")
        return

    print("Session authenticated successfully! ✅")
    
    try:
        # Extract headers directly from your authenticated SDK session object
        access_token = session.access_token
        neo_header = session.neo_header
        
        # Determine the correct base URL based on your SDK environment setup
        base_url = "https://kotakneo.com" if session.environment == "prod" else "https://kotak.com"
        
        # Endpoint to fetch master script links
        file_paths_url = f"{base_url}/script-details/1.0/masterscrip/file-paths"
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Neo-Header": neo_header,
            "Content-Type": "application/json"
        }
        
        print("Fetching Master Scrip downloadable file links...")
        response = requests.get(file_paths_url, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            fno_file_url = None
            
            # Find the NSE F&O (Futures & Options) link in the list
            for item in data.get("data", []):
                if item.get("exchange") == "nse_fo":
                    fno_file_url = item.get("filePath")
                    break
            
            if fno_file_url:
                print(f"Downloading file directly from Kotak servers: {fno_file_url}")
                
                # Fetch the actual CSV from the provided link
                df = pd.read_csv(fno_file_url)
                
                # Strip spaces from column headers to prevent key mismatch bugs
                df.columns = df.columns.str.strip()
                
                output_filename = "kotak_neo_nse_fo_tokens.csv"
                df.to_csv(output_filename, index=False)
                
                print(f"\nSuccess! File saved cleanly as '{output_filename}' in your folder. ✅")
                print("--- Data Preview ---")
                print(df.head(5))
                
            else:
                print("Could not find the 'nse_fo' exchange segment in the response data.")
                print(f"Server response was: {data}")
        else:
            print(f"Failed to fetch paths. HTTP Status: {response.status_code}")
            print(f"Error Message: {response.text}")
            
    except AttributeError:
        print("Error: Unable to find access_token or neo_header attributes inside the SDK session.")
        print("Please check your neo_api_client version.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    download_futures_tokens_direct()
