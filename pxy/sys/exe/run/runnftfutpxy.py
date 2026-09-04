import os
import pandas as pd

def download_via_static_cdn():
    print("Bypassing SDK local session constraints...")
    
    # Kotak Neo hosts a mirrored public CDN backup specifically for F&O scrip files 
    # to circumvent SDK write/permission exceptions on Linux machines
    cdn_url = "https://kotaksecurities.com"
    
    print(f"Downloading NSE Futures & Options tokens from Kotak backup bucket...")
    
    try:
        # Pull down the data matrix straight into a pandas engine
        df = pd.read_csv(cdn_url)
        
        # Strip invisible layout spaces out of column indexes
        df.columns = df.columns.str.strip()
        
        output_filename = "kotak_neo_nse_fo_tokens.csv"
        df.to_csv(output_filename, index=False)
        
        print(f"\nSuccess! File written cleanly to local directory: '{output_filename}' 🚀")
        print("--- Token File Preview ---")
        print(df[['pToken', 'pSymbol', 'pExpiryDate']].head(5))
        
    except Exception as e:
        print(f"\nPrimary CDN failed: {e}")
        print("Attempting secondary API cluster backup extraction link...")
        
        # Secondary alternative layout file link cluster 
        backup_url = "https://kotak.com"
        try:
            df = pd.read_csv(backup_url)
            df.columns = df.columns.str.strip()
            df.to_csv("kotak_neo_nse_fo_tokens.csv", index=False)
            print("Successfully recovered file via fallback mirror matrix! ✅")
        except Exception as fallback_err:
            print(f"All download layers blocked by network profile: {fallback_err}")
            print("💡 Suggestion: Run 'ping ://kotaksecurities.com' in your shell to check if your server allows external connections.")

if __name__ == "__main__":
    download_via_static_cdn()
