
from runclntpxy import get_session
from datetime import datetime, timedelta
import csv
import os

# ============================================================
# CONFIG
# ============================================================
EXCHANGE_SEGMENT = "nse_fo"
CSV_FILE = "nifty_fut.csv"


# ============================================================
# EXPIRY MANAGEMENT (NSE Last Tuesday Framework)
# ============================================================
def last_tuesday(year, month):
    """Calculates the absolute last Tuesday of any given month/year."""
    if month == 12:
        next_month = datetime(year + 1, 1, 1)
    else:
        next_month = datetime(year, month + 1, 1)

    day = next_month - timedelta(days=1)

    # 1 represents Tuesday in Python's datetime.weekday() (0=Monday, 1=Tuesday)
    while day.weekday() != 1:
        day -= timedelta(days=1)

    return day


def get_current_month_expiry():
    """Returns target expiry date. Rolls over if today is past current expiry."""
    now = datetime.now()
    expiry = last_tuesday(now.year, now.month)

    # If the last Tuesday of this month has already passed, shift tracking to next month
    if now.date() > expiry.date():
        if now.month == 12:
            expiry = last_tuesday(now.year + 1, 1)
        else:
            expiry = last_tuesday(now.year, now.month + 1)

    return expiry


# ============================================================
# SEARCH RESULT NORMALIZATION
# ============================================================
def normalize_results(response):
    """Safely normalizes varied API data payloads into clean lists."""
    if isinstance(response, list):
        return response
    if isinstance(response, dict):
        data = response.get("data", [])
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            return [data]
    return []


# ============================================================
# SEARCH NIFTY FUTURE
# ============================================================
def search_nifty_future(client, expiry):
    print("🔎 Searching NIFTY...")
    try:
        response = client.search_scrip(
            exchange_segment=EXCHANGE_SEGMENT,
            symbol="NIFTY"
        )
    except Exception as e:
        print(f"❌ Search error: {e}")
        return None

    results = normalize_results(response)
    if not results:
        print("❌ No search results returned from API")
        return None

    print(f"✅ Total Search Results: {len(results)}")

    # Format Example: NIFTY26OCTFUT
    expected_symbol = (
        f"NIFTY"
        f"{expiry.strftime('%y')}"
        f"{expiry.strftime('%b').upper()}"
        f"FUT"
    )

    print(f"Targeting Symbol : {expected_symbol}")

    for row in results:
        if not isinstance(row, dict):
            continue

        symbol = str(row.get("pTrdSymbol") or "").upper().strip()

        if symbol == expected_symbol:
            return row

    print("❌ Target NIFTY FUT contract variant not found in search results")
    return None


# ============================================================
# SAVE TOKEN CSV
# ============================================================
def save_futures_csv(row):
    fields = ["symbol", "token", "expiry", "lot_size"]
    try:
        with open(CSV_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            writer.writerow({
                "symbol": row.get("pTrdSymbol"),
                "token": row.get("pSymbol"),
                "expiry": row.get("pExpiryDate"),
                "lot_size": row.get("lLotSize")
            })
        print(f"💾 Cached Contract Locally: {CSV_FILE}")
    except Exception as e:
        print(f"❌ Failed to write cache file: {e}")


# ============================================================
# READ TOKEN CSV
# ============================================================
def read_futures_csv():
    if not os.path.exists(CSV_FILE):
        return None
    try:
        with open(CSV_FILE, "r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            row = next(reader, None)
            return row if row else None
    except Exception as e:
        print(f"❌ CSV read error: {e}")
        return None


# ============================================================
# CHECK CACHED CONTRACT
# ============================================================
def cached_contract_valid(row, current_expiry):
    if not row:
        return False

    token = str(row.get("token") or "").strip()
    expiry_text = str(row.get("expiry") or "").strip()

    if not token or not expiry_text:
        return False

    try:
        # Multi-format fallback parsing logic for the cached date string
        if "-" in expiry_text:
            cached_expiry = datetime.strptime(expiry_text, "%Y-%m-%d")
        else:
            cached_expiry = datetime.strptime(expiry_text, "%d%b%Y")
    except ValueError:
        try:
            cached_expiry = datetime.strptime(expiry_text, "%d-%b-%Y")
        except ValueError:
            return False

    return cached_expiry.date() >= current_expiry.date()


# ============================================================
# GET MID PRICE
# ============================================================
def get_mid_price(client, token: str, segment: str = "nse_fo") -> float:
    """Calculates real-time bid/ask spread mid-price or falls back to LTP."""
    try:
        instr = [{"instrument_token": str(token), "exchange_segment": segment}]
        res = client.quotes(instrument_tokens=instr, quote_type="depth")

        if not res or not isinstance(res, list) or len(res) == 0:
            return 0.0

        data = res[0]
        depth = data.get("depth", {})
        buy_list = depth.get("buy", [])
        sell_list = depth.get("sell", [])

        # Fetch front of the order book queue
        bid = float(buy_list[0].get("price", 0)) if buy_list else 0.0
        ask = float(sell_list[0].get("price", 0)) if sell_list else 0.0

        if bid > 0 and ask > 0:
            return round((bid + ask) / 2, 2)

        return float(data.get("last_price", 0))
    except Exception as e:
        print(f"❌ Market data price error: {e}")
        return 0.0


# ============================================================
# GET / CREATE FUTURES CONTRACT
# ============================================================
def get_nifty_future(client):
    current_expiry = get_current_month_expiry()
    print(f"Target Expiry Timeframe : {current_expiry.strftime('%d-%b-%Y')}")

    # 1. Evaluate cache viability
    cached = read_futures_csv()
    if cached:
        if cached_contract_valid(cached, current_expiry):
            print("📄 Using valid cached contract structure")
            return cached
        print("⚠️ Cached contract has expired")
    else:
        print("📄 No cached contract layout discovered")

    # 2. Fetch fresh token from broker lookup map
    row = search_nifty_future(client, current_expiry)
    if row is None:
        return None

    # 3. Commit schema record to disk
    save_futures_csv(row)
    return {
        "symbol": row.get("pTrdSymbol"),
        "token": row.get("pSymbol"),
        "expiry": row.get("pExpiryDate"),
        "lot_size": row.get("lLotSize")
    }


# ============================================================
# ENTRY POINT RUNNER
# ============================================================
def main():
    print("\n" + "=" * 55)
    print("PXY - NIFTY FUTURE LIVE PRICE MODULE")
    print("=" * 55)

    client = get_session()
    if client is None:
        print("❌ System session authentication failed")
        return

    future = get_nifty_future(client)
    if future is None:
        print("❌ Critical: Unable to verify target NIFTY FUT contract metadata")
        return

    token = future["token"]
    symbol = future["symbol"]

    print(f"\n📡 Requesting stream quote for : {symbol} [Token: {token}]")
    price = get_mid_price(client, token, EXCHANGE_SEGMENT)

    if price <= 0:
        print("❌ Execution halted: Verified price is unavailable or out-of-bounds")
        return

    print("\n" + "=" * 55)
    print("📈 LIVE MATRIX UPDATE")
    print("=" * 55)
    print(f"Symbol   : {symbol}")
    print(f"Token    : {token}")
    print(f"Expiry   : {future['expiry']}")
    print(f"Mid Price: {price:.2f}")
    print("=" * 55 + "\n")


if __name__ == "__main__":
    main()

