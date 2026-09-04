import os
import urllib.request
import pandas as pd
import io
import socket

# 1. Local Networking DNS Override
# This forces the script to bypass broken machine DNS routing 
# and connects directly to Kotak Securities' active hosting network cluster.
def override_kotak_dns():
    try:
        def custom_getaddrinfo(*args, **kwargs):
            host = args[0]
            if host == "://kotaksecurities.com":
                return [(socket.AF_INET, socket.SOCK_STREAM, 6, '', ('203.199.231.111', 443))]
            return original_getaddrinfo(*args, **kwargs)
            
        original_getaddrinfo = socket.getaddrinfo
        socket.getaddrinfo = custom_getaddrinfo
        print("DNS mapping override applied successfully! 🌐")
    except Exception as e:
        print(f"Could not hook network layer: {e}")

def download_clean_futures_master():
    override_kotak_dns()
    
    # Target URL containing raw data streams
    cdn_url = "https://://kotaksecurities.com/tradeweb/MasterAndTokenFiles/ScripMaster/nse_fo.csv"
    
    # Pass precise header layouts to tell Kotak's engine to send data, not a webpage webpage layout.
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'text/csv,application/csv,application/octet-stream,*/*',
        'Accept-Language': 'en-US,en;q=0.9',
        'Connection': 'keep-alive'
    }
    
    try:
        print("Streaming file structure from Kotak central vault...")
        req = urllib.request.Request(cdn_url, headers=headers)
        
        with urllib.request.urlopen(req, timeout=30) as response:
            raw_bytes = response.read()
            
        # Decode ignoring broken layout structures
        raw_text = raw_bytes.decode('utf-8', errors='ignore').strip()
        
        # Guard rails: Verify we actually grabbed data instead of an HTML document structure
        if raw_text.startswith("<!DOCTYPE") or "<html" in raw_text[:200]:
            print("\n❌ Warning: Server returned an HTML block page instead of the dataset.")
            print("Kotak's public CDN server is blocking unauthorized requests right now.")
            return

        print("Data loaded perfectly! Extracting matrix...")
        
        # Read the text layout directly into Pandas using a comma separator layout
        df = pd.read_csv(io.StringIO(raw_text), sep=',', on_bad_lines='skip', low_memory=False)
        df.columns = df.columns.str.strip()
        
        output_filename = "kotak_neo_nse_fo_tokens.csv"
        df.to_csv(output_filename, index=False)
        
        print(f"\nSuccess! File written cleanly to local directory: '{output_filename}' 🚀")
        print(f"Total Rows Parsed: {len(df)}")
        print("\n--- Data Sample ---")
        print(df[['pToken', 'pSymbol', 'pExpiryDate']].dropna().head(5))
        
    except Exception as e:
        print(f"\nProcessing system error occurred: {e}")

if __name__ == "__main__":
    download_clean_futures_master()
