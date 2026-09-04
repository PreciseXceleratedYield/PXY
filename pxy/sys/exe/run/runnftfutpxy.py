import pandas as pd
# Import your authenticated session function from runclntpxy.py
from runclntpxy import get_session 

def download_futures_tokens():
    print("Initializing session via runclntpxy...")
    # 1. Reuse your working session login
    session = get_session()
    
    if not session:
        print("Error: Could not authenticate session. Check credentials.")
        return

    print("Session authenticated successfully! ✅")
    
    try:
        # 2. Call the SDK's built-in scrip_master method.
        # Passing 'nse_fo' targets the National Stock Exchange - Futures & Options segment.
        print("Downloading Scrip Master CSV for 'nse_fo'...")
        
        # This downloads and writes the file directly into your local directory.
        session.scrip_master(exchange_segment="nse_fo")
        
        print("Download complete! The CSV file has been saved in your current folder.")
        
    except Exception as e:
        print(f"An error occurred while downloading the scrip master: {e}")

if __name__ == "__main__":
    download_futures_tokens()

