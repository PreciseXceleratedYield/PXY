import urllib.request
import pandas as pd
import io

def download_raw_stream_cdn():
    print("Bypassing SDK file handlers...")
    
    # Target URL for the NSE F&O Master file
    cdn_url = "https://kotaksecurities.com"
    
    # Use custom browser agent headers to prevent 'HTTP 403 Forbidden' layout rejections
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    try:
        print("Streaming raw content from Kotak repository...")
        req = urllib.request.Request(cdn_url, headers=headers)
        
        with urllib.request.urlopen(req, timeout=30) as response:
            # Read everything as a raw byte array chunk
            raw_bytes = response.read()
            
        print("Download successful! Decoding byte contents...")
        
        # Safely convert raw bytes to text lines using utf-8 (ignoring corrupt characters)
        raw_text = raw_bytes.decode('utf-8', errors='ignore')
        
        # Split it into individual rows
        lines = raw_text.splitlines()
        print(f"Total entries discovered in stream: {len(lines)}")
        
        if len(lines) < 2:
            print("Error: Downloaded data payload is completely empty.")
            return

        # Check the top data row structure to see what delimiter Kotak is using (comma vs pipe)
        sample_line = lines[1]
        delimiter = '|' if '|' in sample_line else ','
        print(f"Detected internal file delimiter: '{delimiter}'")
        
        # Feed the text structure safely into Pandas using the exact parsed delimiter layout
        print("Structuring data frame lines matrix...")
        df = pd.read_csv(io.StringIO(raw_text), sep=delimiter, on_bad_lines='skip', low_memory=False)
        
        # Clear trailing spaces from headers
        df.columns = df.columns.str.strip()
        
        output_filename = "kotak_neo_nse_fo_tokens.csv"
        df.to_csv(output_filename, index=False)
        
        print(f"\nSuccess! File written cleanly to local directory: '{output_filename}' 🚀")
        print("--- Token File Columns Found ---")
        print(list(df.columns[:8]))
        print("\n--- Top Data Sample ---")
        print(df.head(3))
        
    except Exception as e:
        print(f"\nProcessing system failed: {e}")
        print("Please check your local workspace storage parameters.")

if __name__ == "__main__":
    download_raw_stream_cdn()
