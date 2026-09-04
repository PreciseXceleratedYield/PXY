import csv
import os
from datetime import datetime, timedelta
# Import your authenticated session function from runclntpxy.py
from runclntpxy import get_session

# ============================================================
# CONFIG
# ============================================================
EXCHANGE_SEGMENT = "nse_fo"
CSV_FILE = "nifty_fut.csv"


# ============================================================
# LOGISTIC HELPERS (Expiry, Normalization, & Search)
# ============================================================
def last_tuesday(year, month):
    """Calculates the last Tuesday of a given month and year."""
    if month == 12:
        next_month = datetime(year + 1, 1, 1)
    else:
        next_month = datetime(year, month + 1, 1)

    day = next_month - timedelta(days=1)
    while day.weekday() != 1:  # 1 represents Tuesday
        day -= timedelta(days=1)
    return day


def get_current_month_expiry():
    """Identifies whether to target the current month or next month's contract."""
    now = datetime.now()
    expiry = last_tuesday(now.year, now.month)

    # If current month's expiry has passed, move to next month.
    if now.date() > expiry.date():
        if now.month == 12:
            expiry = last_tuesday(now.year + 1, 1)
        else:
            expiry = last_tuesday(now.year, now.month + 1)
    return expiry


def normalize_results(response):
    """Normalizes the Kotak SDK variant response payloads."""
    if isinstance(response, list):
        return response
    if isinstance(response, dict):
        data = response.get("data",)
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            return [data]
    return


def search_nifty_future(client, expiry):
    """Hits the master scrip engine to resolve a missing contract."""
    print("🔎 Searching NIFTY...")
    try:
        response = client.search_scrip(
            exchange_segment=EXCHANGE_SEGMENT, symbol="NIFTY"
        )
    except Exception as e:
        print(f"❌ Search error: {e}")
        return None

    results = normalize_results(response)
    if not results:
        print("❌ No search results")
        return None

    print(f"✅ Search results : {len(results)}")

    expected_symbol = (
        f"NIFTY"
        f"{expiry.strftime('%y')}"
        f"{expiry.strftime('%b').upper()}"
        f"FUT"
    )
    print(f"Looking for     : {expected_symbol}")

    for row in results:
        if not isinstance(row, dict):
            continue
        symbol = str(row.get("pTrdSymbol") or "").upper()
        if symbol == expected_symbol:
            return row

    print("❌ Current NIFTY FUT not found")
    return None


# ============================================================
# CACHE I/O IMPLEMENTATIONS
# ============================================================
def save_futures_csv(row):
    """Saves a fresh contract token to local storage."""
    fields = ["symbol", "token", "expiry", "lot_size"]
    with open(CSV_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerow({
            "symbol": row.get("pTrdSymbol"),
            "token": row.get("pSymbol"),
            "expiry": row.get("pExpiryDate"),
            "lot_size": row.get("lLotSize"),
        })
    print(f"💾 Saved : {CSV_FILE}")


def read_futures_csv():
    """Reads the stored contract parameters from disk."""
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


def cached_contract_valid(row, current_expiry):
    """Validates if the cached contract has passed its expiration limit."""
    if not row:
        return False
    token = str(row.get("token") or "").strip()
    expiry_text = str(row.get("expiry") or "").strip()

    if not token or not expiry_text:
        return False
    try:
        cached_expiry = datetime.strptime(expiry_text, "%d%b%Y")
    except ValueError:
        return False

    return cached_expiry.date() >= current_expiry.date()


# ============================================================
# INTERFACE FETCH METRICS
# ============================================================
def get_mid_price(client, token: str, segment: str = "nse_fo") -> float:
    """Gets market depth and calculates mid-price or falls back to last_price."""
    try:
        instr = [
            {"instrument_token": str(token), "exchange_segment": segment}
        ]
        res = client.quotes(instrument_tokens=instr, quote_type="depth")

        if not res or not isinstance(res, list) or len(res) == 0:
            return 0.0

        data = res
        depth = data.get("depth", {})
        buy_list = depth.get("buy",)
        sell_list = depth.get("sell",)

        bid = float(buy_list.get("price", 0)) if buy_list else 0.0
        ask = float(sell_list.get("price", 0)) if sell_list else 0.0

        if bid > 0 and ask > 0:
            return round((bid + ask) / 2, 2)

        return float(data.get("last_price", 0))
    except Exception as e:
        print(f"❌ Price error: {e}")
        return 0.0


def get_nifty_future(client):
    """Resolves the current valid future contract via local cache or API search."""
    current_expiry = get_current_month_expiry()
    print(f"Expiry : {current_expiry.strftime('%d-%b-%Y')}")

    # Check local file storage
    cached = read_futures_csv()
    if cached:
        if cached_contract_valid(cached, current_expiry):
            print("📄 Using cached contract")
            print(f"Symbol : {cached['symbol']}")
            print(f"Token  : {cached['token']}")
            print(f"Expiry : {cached['expiry']}")
            return cached
        print("⚠️ Cached contract expired")
    else:
        print("📄 No cached contract found")

    # Run network fallback scrip check when required
    row = search_nifty_future(client, current_expiry)
    if row is None:
        return None

    save_futures_csv(row)
    return {
        "symbol": row.get("pTrdSymbol"),
        "token": row.get("pSymbol"),
        "expiry": row.get("pExpiryDate"),
        "lot_size": row.get("lLotSize"),
    }


# ============================================================
# THE CORE CALLABLE FUNCTION
# ============================================================
def get_live_nifty_future_price() -> tuple:
    """The complete interface callable function block.

    Returns:
        tuple: (price, token, symbol, expiry) if successful, else (0.0, None,
        None, None)
    """
    client = get_session()
    if client is None:
        print("❌ Login failed")
        return 0.0, None, None, None

    future = get_nifty_future(client)
    if future is None:
        print("❌ Unable to get NIFTY FUT contract")
        return 0.0, None, None, None

    token = future["token"]
    symbol = future["symbol"]
    expiry = future["expiry"]

    price = get_mid_price(client, token, EXCHANGE_SEGMENT)
    if price <= 0:
        print("❌ Price not available")
        return 0.0, token, symbol, expiry

    return price, token, symbol, expiry


# ============================================================
# EXECUTION ENTRY WRAPPER
# ============================================================
if __name__ == "__main__":
    print()
    print("=" * 55)
    print("PXY - NIFTY FUTURE LIVE PRICE ENGINE")
    print("=" * 55)

    # Simple clean inline unpack call
    live_price, active_token, target_symbol, active_expiry = (
        get_live_nifty_future_price()
    )

    if live_price > 0:
        print()
        print("=" * 55)
        print("📈 NIFTY FUTURE DATA CAPTURED")
        print("=" * 55)
        print(f"Symbol : {target_symbol}")
        print(f"Token  : {active_token}")
        print(f"Expiry : {active_expiry}")
        print(f"Price  : ₹ {live_price:.2f}")
        print("=" * 55)
        print()

