import yfinance as yf

def get_gift_nifty_live():
    try:
        # 'FN=F' is the continuous contract ticker for GIFT NIFTY on Yahoo Finance
        ticker = yf.Ticker("FN=F")
        
        # Fetch the latest 1-minute bar data
        df = ticker.history(period="1d", interval="1m")
        
        if not df.empty:
            latest_candle = df.iloc[-1]
            print("===== GIFT NIFTY LIVE DATA =====")
            print(f"Latest LTP : {latest_candle['Close']:.2f}")
            print(f"Open       : {latest_candle['Open']:.2f}")
            print(f"High       : {latest_candle['High']:.2f}")
            print(f"Low        : {latest_candle['Low']:.2f}")
            print(f"Volume     : {int(latest_candle['Volume'])}")
        else:
            print("No live data available for FN=F right now.")
    except Exception as e:
        print(f"Error fetching GIFT NIFTY data: {e}")

if __name__ == "__main__":
    get_gift_nifty_live()


