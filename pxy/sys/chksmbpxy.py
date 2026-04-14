# run_loop.py
import time
import yfinance as yf
from sysdashpxy import get_full_snapshot, print_dashboard  # ✅ your original functions

# ================= FETCH =================
def fetch_yf_data(symbol):
    try:
        ticker = yf.Ticker(symbol)

        # 1️⃣ primary
        df = ticker.history(interval="1m", period="1d")

        # 2️⃣ fallback
        if df is None or df.empty:
            df = ticker.history(interval="1m", period="5d")

        # 3️⃣ final fallback
        if df is None or df.empty:
            df = ticker.history(interval="5m", period="5d")

        if df is None or df.empty:
            print(f"❌ No data for {symbol}")
            return None

        return df

    except Exception as e:
        print(f"YF Error ({symbol}):", e)
        return None


# ================= MAIN LOOP =================
if __name__ == "__main__":
    symbol = input("Enter Symbol: ").strip()

    while True:
        df = fetch_yf_data(symbol)

        if df is not None:
            # ✅ pass df EXACTLY like your original system expects
            data = get_full_snapshot(df=df)
            print_dashboard(data)
        else:
            print("No data fetched.")

        time.sleep(6)
