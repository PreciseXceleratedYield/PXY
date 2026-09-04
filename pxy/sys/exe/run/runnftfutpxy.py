import json
import yfinance as yf
from colorama import Fore, Style, init

# Initialize terminal color hooks
init(autoreset=True)

def get_gift_nifty_live_price():
    """
    Fetches the precise live execution metrics for GIFT NIFTY
    using the updated Yahoo Finance ticker mapping to prevent 404 errors.
    """
    # 🎯 THE FIX: Changed 'FN=F' to 'IN=F' (NSE IX India 50 Continuous Future Ticker)
    UPDATED_GIFT_TICKER = "IN=F"
    
    print(f"📡 Ingesting live feed matrix for GIFT NIFTY via: {Fore.CYAN}{UPDATED_GIFT_TICKER}")
    
    try:
        ticker = yf.Ticker(UPDATED_GIFT_TICKER)
        
        # Pull the latest 1-day bar frame with 1-minute candle resolution
        df = ticker.history(period="1d", interval="1m")
        
        if not df.empty:
            # Isolate the current running candle layer
            latest_candle = df.iloc[-1]
            
            # Extract standard OHLC metrics cleanly
            ltp = float(latest_candle['Close'])
            open_prc = float(latest_candle['Open'])
            high_prc = float(latest_candle['High'])
            low_prc = float(latest_candle['Low'])
            volume = int(latest_candle['Volume'])
            
            # Construct a clean JSON-parsable output block
            metrics_payload = {
                "symbol": "GIFTNIFTY_CONTINUOUS",
                "exchange": "NSE_IX",
                "last_price": f"{ltp:.2f}",
                "ohlc": {
                    "open": f"{open_prc:.2f}",
                    "high": f"{high_prc:.2f}",
                    "low": f"{low_prc:.2f}"
                },
                "volume": volume
            }
            
            print(f"\n{Fore.YELLOW}================ GIFT NIFTY LIVE RESULTS ================")
            print(json.dumps(metrics_payload, indent=4))
            print(f"{Fore.YELLOW}=========================================================\n")
            
        else:
            print(f"{Fore.RED}❌ Error: Empty dataset returned. The market segment might be between sessions.")

    except Exception as e:
        print(f"{Fore.RED}❌ Network Pipeline Connection Failure: {e}")

if __name__ == "__main__":
    get_gift_nifty_live_price()

