
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
# EXPIRY
# ============================================================

def last_tuesday(year, month):

    if month == 12:
        next_month = datetime(year + 1, 1, 1)
    else:
        next_month = datetime(year, month + 1, 1)

    day = next_month - timedelta(days=1)

    while day.weekday() != 1:
        day -= timedelta(days=1)

    return day


def get_current_month_expiry():

    now = datetime.now()

    expiry = last_tuesday(
        now.year,
        now.month
    )

    # If current month's expiry has passed,
    # move to next month.
    if now.date() > expiry.date():

        if now.month == 12:
            expiry = last_tuesday(
                now.year + 1,
                1
            )
        else:
            expiry = last_tuesday(
                now.year,
                now.month + 1
            )

    return expiry


# ============================================================
# SEARCH RESULT NORMALIZATION
# ============================================================

def normalize_results(response):

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

        print("❌ No search results")
        return None

    print(
        f"✅ Search results : {len(results)}"
    )

    expected_symbol = (
        f"NIFTY"
        f"{expiry.strftime('%y')}"
        f"{expiry.strftime('%b').upper()}"
        f"FUT"
    )

    print(
        f"Looking for     : {expected_symbol}"
    )

    for row in results:

        if not isinstance(row, dict):
            continue

        symbol = str(
            row.get("pTrdSymbol") or ""
        ).upper()

        if symbol == expected_symbol:

            return row

    print(
        "❌ Current NIFTY FUT not found"
    )

    return None


# ============================================================
# SAVE TOKEN CSV
# ============================================================

def save_futures_csv(row):

    fields = [
        "symbol",
        "token",
        "expiry",
        "lot_size"
    ]

    with open(
        CSV_FILE,
        "w",
        newline="",
        encoding="utf-8"
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=fields
        )

        writer.writeheader()

        writer.writerow({
            "symbol": row.get("pTrdSymbol"),
            "token": row.get("pSymbol"),
            "expiry": row.get("pExpiryDate"),
            "lot_size": row.get("lLotSize")
        })

    print(f"💾 Saved : {CSV_FILE}")


# ============================================================
# READ TOKEN CSV
# ============================================================

def read_futures_csv():

    if not os.path.exists(CSV_FILE):
        return None

    try:

        with open(
            CSV_FILE,
            "r",
            newline="",
            encoding="utf-8"
        ) as f:

            reader = csv.DictReader(f)

            row = next(reader, None)

            if not row:
                return None

            return row

    except Exception as e:

        print(f"❌ CSV read error: {e}")
        return None


# ============================================================
# CHECK CACHED CONTRACT
# ============================================================

def cached_contract_valid(row, current_expiry):

    if not row:
        return False

    token = str(
        row.get("token") or ""
    ).strip()

    expiry_text = str(
        row.get("expiry") or ""
    ).strip()

    if not token or not expiry_text:
        return False

    try:

        cached_expiry = datetime.strptime(
            expiry_text,
            "%d%b%Y"
        )

    except ValueError:

        return False

    return (
        cached_expiry.date()
        >= current_expiry.date()
    )


# ============================================================
# GET MID PRICE
# ============================================================

def get_mid_price(
    client,
    token: str,
    segment: str = "nse_fo"
) -> float:

    """
    Gets depth and calculates bid/ask mid-price.
    Falls back to last_price if depth is unavailable.
    """

    try:

        instr = [
            {
                "instrument_token": str(token),
                "exchange_segment": segment
            }
        ]

        res = client.quotes(
            instrument_tokens=instr,
            quote_type="depth"
        )

        if (
            not res
            or not isinstance(res, list)
            or len(res) == 0
        ):
            return 0.0

        data = res[0]

        depth = data.get("depth", {})

        buy_list = depth.get("buy", [])
        sell_list = depth.get("sell", [])

        bid = (
            float(
                buy_list[0].get("price", 0)
            )
            if buy_list
            else 0.0
        )

        ask = (
            float(
                sell_list[0].get("price", 0)
            )
            if sell_list
            else 0.0
        )

        if bid > 0 and ask > 0:

            return round(
                (bid + ask) / 2,
                2
            )

        return float(
            data.get("last_price", 0)
        )

    except Exception as e:

        print(f"❌ Price error: {e}")
        return 0.0


# ============================================================
# GET / CREATE FUTURES CONTRACT
# ============================================================

def get_nifty_future(client):

    current_expiry = get_current_month_expiry()

    print(
        f"Expiry : "
        f"{current_expiry.strftime('%d-%b-%Y')}"
    )

    # --------------------------------------------------------
    # FIRST: CHECK LOCAL CSV
    # --------------------------------------------------------

    cached = read_futures_csv()

    if cached:

        if cached_contract_valid(
            cached,
            current_expiry
        ):

            print("📄 Using cached contract")
            print(
                f"Symbol : {cached['symbol']}"
            )
            print(
                f"Token  : {cached['token']}"
            )
            print(
                f"Expiry : {cached['expiry']}"
            )

            return cached

        print(
            "⚠️ Cached contract expired"
        )

    else:

        print(
            "📄 No cached contract found"
        )

    # --------------------------------------------------------
    # SEARCH ONLY WHEN REQUIRED
    # --------------------------------------------------------

    row = search_nifty_future(
        client,
        current_expiry
    )

    if row is None:
        return None

    # --------------------------------------------------------
    # SAVE NEW CONTRACT
    # --------------------------------------------------------

    save_futures_csv(row)

    return {
        "symbol": row.get("pTrdSymbol"),
        "token": row.get("pSymbol"),
        "expiry": row.get("pExpiryDate"),
        "lot_size": row.get("lLotSize")
    }


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("=" * 55)
    print("PXY - NIFTY FUTURE LIVE PRICE")
    print("=" * 55)

    # --------------------------------------------------------
    # LOGIN
    # --------------------------------------------------------

    client = get_session()

    if client is None:

        print("❌ Login failed")
        return

    # --------------------------------------------------------
    # GET CONTRACT
    # --------------------------------------------------------

    future = get_nifty_future(client)

    if future is None:

        print(
            "❌ Unable to get NIFTY FUT contract"
        )

        return

    token = future["token"]
    symbol = future["symbol"]

    # --------------------------------------------------------
    # DIRECT PRICE USING CACHED TOKEN
    # --------------------------------------------------------

    print()
    print(
        f"📡 Getting price : {symbol}"
    )

    price = get_mid_price(
        client,
        token,
        EXCHANGE_SEGMENT
    )

    if price <= 0:

        print("❌ Price not available")
        return

    # --------------------------------------------------------
    # OUTPUT
    # --------------------------------------------------------

    print()
    print("=" * 55)
    print("📈 NIFTY FUTURE")
    print("=" * 55)

    print(f"Symbol : {symbol}")
    print(f"Token  : {token}")
    print(f"Expiry : {future['expiry']}")
    print(f"Price  : {price:.2f}")

    print("=" * 55)
    print()


if __name__ == "__main__":
    main()

