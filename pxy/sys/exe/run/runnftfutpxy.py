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
        # Extract the headers map that the NeoAPI class uses internally
        # By default, Kotak SDK packages authorization data into 'session.headers'
        sdk_headers = getattr(session, "headers", {})
        
        # Pull key values out cleanly
        access_token = sdk_headers.get("Authorization")
        neo_header = sdk_headers.get("Neo-Header")
        
        # Fallback safeguard in case token extraction fails
        if not access_token or not neo_header:
            print("Direct header extract failed. Attempting fallback mapping keys...")
            access_token = getattr(session, "access_token", None) or sdk_headers.get("bearer")
            neo_header = getattr(session, "neo_header", None) or sdk_headers.get("neo-header")

        # Determine the environment API URL
        base_url = "https://api.kotakneo.com" if getattr(session, "environment", "prod") == "prod" else "https://kotak.com"
        file_paths_url = f"{base_url}/script-details/1.0/masterscrip/file-paths"
        
        # Build clean request parameters
        headers = {
            "Authorization": access_token if "Bearer" in str(access_token) else f"Bearer {access_token}",
            "Neo-Header": neo_header,
            "Content-Type": "application/json"
        }
        
        print("Fetching Master Scrip downloadable file links...")
        response = requests.get(file_paths_url, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            fno_file_url = None
            
            # Locate the NSE Futures and Options (nse_fo) CSV path
            for item in data.get("data", []):
                if item.get("exchange") == "nse_fo":
                    fno_file_url = item.get("filePath")
                    break
            
            if fno_file_url:
                print(f"Downloading file directly from Kotak servers: {fno_file_url}")
                
                # Read and standardize the CSV file data
                df = pd.read_csv(fno_file_url)
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
            
    except Exception as e:
        print(f"An unexpected error occurred during processing: {e}")

if __name__ == "__main__":
    download_futures_tokens_direct()

