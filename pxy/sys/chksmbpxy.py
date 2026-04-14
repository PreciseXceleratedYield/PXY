# chksmbpxy.py
import time
import yfinance as yf
import sysdashpxy   # ✅ import full module

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
            # 🔥 MONKEY PATCH (override internal fetch)
            sysdashpxy.fetch_yf_data = lambda: df

            # ✅ call original EXACT function
            data = sysdashpxy.get_full_snapshot()
            sysdashpxy.print_dashboard(data)

        else:
            print("No data fetched.")

        time.sleep(6)
