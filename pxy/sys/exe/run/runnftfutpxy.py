import os
import shutil
import glob
# Import your authenticated session function from runclntpxy.py
from runclntpxy import get_session 

def export_kotak_tokens():
    print("Initializing session via runclntpxy...")
    session = get_session()
    
    if not session:
        print("Error: Could not authenticate session. Check credentials.")
        return

    print("Session authenticated successfully! ✅")
    
    try:
        segment = "nse_fo"
        print(f"Requesting '{segment}' Scrip Master using native SDK wrapper...")
        
        # 1. Let the official Kotak Neo SDK handle the download internally 
        session.scrip_master(exchange_segment=segment)
        
        # 2. Automatically locate the hidden file inside neo_api_client directory
        import neo_api_client
        sdk_dir = os.path.dirname(neo_api_client.__file__)
        hidden_data_dir = os.path.join(sdk_dir, "data")
        
        print(f"Scanning internal cache directory: {hidden_data_dir}")
        
        # Look for any .csv files matching 'nse_fo' or 'ScripMaster' inside that folder
        csv_files = glob.glob(os.path.join(hidden_data_dir, f"*{segment}*.csv")) + \
                    glob.glob(os.path.join(hidden_data_dir, "*.csv"))
        
        if csv_files:
            # Pick the newest downloaded master file found
            newest_file = max(csv_files, key=os.path.getctime)
            destination_path = "./kotak_neo_nse_fo_tokens.csv"
            
            # Copy it out cleanly to your current folder
            shutil.copy(newest_file, destination_path)
            print(f"\nSuccess! Token CSV exported cleanly to current folder: '{destination_path}' 🚀")
        else:
            print("\nThe SDK finished executing, but no local CSV file cache was found.")
            print("Please ensure your machine has active internet connectivity.")

    except Exception as e:
        print(f"An unexpected error occurred during processing: {e}")

if __name__ == "__main__":
    export_kotak_tokens()

