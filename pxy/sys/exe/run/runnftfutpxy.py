import os
import pandas as pd
# Import your authenticated session function from runclntpxy.py
from runclntpxy import get_session 

def download_futures_tokens():
    print("Initializing session via runclntpxy...")
    session = get_session()
    
    if not session:
        print("Error: Could not authenticate session. Check credentials.")
        return

    print("Session authenticated successfully! ✅")
    
    try:
        print("Requesting 'nse_fo' Scrip Master data...")
        
        # 1. By default, the SDK method returns the data or internal file info
        # Let's call it and capture its output
        scrip_data = session.scrip_master(exchange_segment="nse_fo")
        
        # 2. Check where the SDK hid the file natively
        # The library saves data to: python_env/lib/site-packages/neo_api_client/data/
        import neo_api_client
        sdk_dir = os.path.dirname(neo_api_client.__file__)
        hidden_csv_path = os.path.join(sdk_dir, "data", "nse_fo.csv")
        
        output_filename = "kotak_neo_nse_fo_tokens.csv"

        if os.path.exists(hidden_csv_path):
            # 3. Read it from the hidden directory and save a copy here!
            df = pd.read_csv(hidden_csv_path)
            df.to_csv(output_filename, index=False)
            print(f"Success! Found SDK cache and saved it locally as: '{output_filename}' ✅")
            print("\nFirst 5 rows of your tokens:")
            print(df.head(5))
        else:
            # Fallback if your SDK version treats the return structure as text/json
            if scrip_data:
                print("SDK did not write a file but returned data. Writing file manually...")
                # Assuming standard format, adjust if scrip_data is a direct list/dict
                df = pd.DataFrame(scrip_data)
                df.to_csv(output_filename, index=False)
                print(f"Saved data manually to '{output_filename}' ✅")
            else:
                print("The SDK executed but did not return data or cache a file. Verify exchange segment name.")
                
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    download_futures_tokens()
