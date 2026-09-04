import os
import requests
import pandas as pd
# Import your authenticated session function from runclntpxy.py
from runclntpxy import get_session 

def download_futures_tokens_robust():
    print("Initializing session via runclntpxy...")
    session = get_session()
    
    if not session:
        print("Error: Could not authenticate session. Check credentials.")
        return

    print("Session authenticated successfully! ✅")
    
    # --- 1. Dynamic Attribute Investigation ---
    # Find all available internal variables within your live session object
    available_attrs = dir(session)
    
    access_token = None
    neo_header = None
    
    # Scan for common token keys used across different Kotak SDK versions
    for attr in available_attrs:
        lower_attr = attr.lower()
        if "token" in lower_attr and not callable(getattr(session, attr)):
            # Catch token variables (e.g., token, access_token, trading_token)
            if "access" in lower_attr or "bearer" in lower_attr or attr == "token":
                access_token = getattr(session, attr)
        if "header" in lower_attr and not callable(getattr(session, attr)):
            # Catch neo-header layout keys
            neo_header = getattr(session, attr)

    # Manual backup check if string scanning skipped them
    if not access_token:
        access_token = getattr(session, "access_token", None) or getattr(session, "token", None)
    if not neo_header:
        neo_header = getattr(session, "neo_header", None)

    # --- 2. Build HTTP Requests Safely ---
    try:
        # Resolve Base URL endpoint
        env = getattr(session, "environment", "prod")
        base_url = "https://api.kotakneo.com" if env == "prod" else "https://kotak.com"
        file_paths_url = f"{base_url}/script-details/1.0/masterscrip/file-paths"
        
        # Build clean authorization parameters
        # Format token string to guarantee Bearer prefix structure
        auth_string = str(access_token)
        if auth_string and not auth_string.startswith("Bearer "):
            auth_string = f"Bearer {auth_string}"

        headers = {
            "Authorization": auth_string,
            "Neo-Header": str(neo_header),
            "Content-Type": "application/json"
        }
        
        print(f"Using Found Tokens -> Authorization: {auth_string[:20]}... | Neo-Header: {neo_header}")
        print("Fetching master scrip URLs...")
        
        response = requests.get(file_paths_url, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            fno_file_url = None
            
            for item in data.get("data", []):
                if item.get("exchange") == "nse_fo":
                    fno_file_url = item.get("filePath")
                    break
                    
            if fno_file_url:
                print(f"Downloading master file directly from: {fno_file_url}")
                df = pd.read_csv(fno_file_url)
                df.columns = df.columns.str.strip()
                
                output_filename = "kotak_neo_nse_fo_tokens.csv"
                df.to_csv(output_filename, index=False)
                
                print(f"\nSuccess! File written cleanly to local directory: '{output_filename}' 🚀")
                print("--- Data Preview ---")
                print(df.head(3))
            else:
                print("Could not find the 'nse_fo' exchange segment in the Kotak database array.")
                print(f"Server data layout: {data}")
        else:
            print(f"HTTP Request Failed (Status {response.status_code}): {response.text}")
            print("\n💡 Debug: If it says Unauthorized, your SDK uses custom session dicts.")
            print("Listing internal structure properties to help diagnose:")
            for attr in sorted(available_attrs):
                if not attr.startswith("_") and not callable(getattr(session, attr)):
                    print(f" -> session.{attr} = {type(getattr(session, attr)).__name__}")
            
    except Exception as e:
        print(f"An unexpected error occurred during processing: {e}")

if __name__ == "__main__":
    download_futures_tokens_robust()
