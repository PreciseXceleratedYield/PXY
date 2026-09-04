```python
from runclntpxy import get_session
from datetime import datetime, timedelta
import csv


EXCHANGE_SEGMENT = "nse_fo"
CSV_FILE = "nifty_search.csv"


# ============================================================
# EXPIRY
# ============================================================

def last_tuesday(year, month):
    if month == 12:
        next_month = datetime(year + 1, 1, 1)
    else:
        next_month = datetime(year, month + 1, 1)

    day = next_month - timedelta(days=1)

    while day.weekday() != 1:       # Tuesday
        day -= timedelta(days=1)

    return day


def get_current_month_expiry():
    now = datetime.now()

    expiry = last_tuesday(now.year, now.month)

    # If this month's expiry has passed, use next month
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
# DUMP SEARCH RESULTS
# ============================================================

def dump_csv(results):

    if not results:
        return

    fields = set()

    for row in results:
        if isinstance(row, dict):
            fields.update(row.keys())

    fields = sorted(fields)

    with open(
        CSV_FILE,
        "w",
        newline="",
        encoding="utf-8"
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=fields,
            extrasaction="ignore"
        )

        writer.writeheader()

        for row in results:
            if isinstance(row, dict):
                writer.writerow(row)

    print(f"💾 CSV  : {CSV_FILE}")
    print(f"📊 Rows : {len(results)}")


# ============================================================
# FIND CURRENT NIFTY FUTURE
# ============================================================

def find_nifty_future(results, expiry):

    expected_symbol = (
        f"NIFTY"
        f"{expiry.strftime('%y')}"
        f"{expiry.strftime('%b').upper()}"
        f"FUT"
    )

    print(f"Looking for : {expected_symbol}")

    for row in results:

        if not isinstance(row, dict):
            continue

        symbol = str(
            row.get("pTrdSymbol") or ""
        ).upper()

        if symbol == expected_symbol:
            return row

    return None


# ============================================================
# LIVE MID PRICE
# ============================================================

def get_mid_price(
    client,
    token: str,
    segment: str = "nse_fo"
) -> float:

    """
    Gets depth and calculates bid/ask mid-price.
    Falls back to last_price when depth is unavailable.
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
            float(buy_list[0].get("price", 0))
            if buy_list else 0.0
        )

        ask = (
            float(sell_list[0].get("price", 0))
            if sell_list else 0.0
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
    # EXPIRY
    # --------------------------------------------------------

    expiry = get_current_month_expiry()

    print(
        f"Expiry : {expiry.strftime('%d-%b-%Y')}"
    )

    # --------------------------------------------------------
    # SEARCH
    # --------------------------------------------------------

    print("Searching NIFTY...")
    print()

    try:

        response = client.search_scrip(
            exchange_segment=EXCHANGE_SEGMENT,
            symbol="NIFTY"
        )

    except Exception as e:

        print(f"❌ Search error: {e}")
        return

    results = normalize_results(response)

    if not results:

        print("❌ No search results")
        return

    print(
        f"✅ Search results : {len(results)}"
    )

    # --------------------------------------------------------
    # ALWAYS DUMP SEARCH DATA
    # --------------------------------------------------------

    dump_csv(results)

    # --------------------------------------------------------
    # FIND FUTURE
    # --------------------------------------------------------

    future = find_nifty_future(
        results,
        expiry
    )

    if future is None:

        print(
            "❌ Current month NIFTY FUT not found"
        )

        return

    symbol = future.get("pTrdSymbol")
    token = future.get("pSymbol")

    print()
    print("=" * 55)
    print("✅ NIFTY FUT FOUND")
    print("=" * 55)

    print(f"Neo Symbol : {symbol}")
    print(f"pSymbol    : {token}")
    print(
        f"Expiry     : "
        f"{future.get('pExpiryDate')}"
    )
    print(
        f"Lot Size   : "
        f"{future.get('lLotSize')}"
    )

    # --------------------------------------------------------
    # LIVE PRICE
    # --------------------------------------------------------

    price = get_mid_price(
        client,
        str(token),
        EXCHANGE_SEGMENT
    )

    if price <= 0:

        print("❌ LTP not found")
        return

    # --------------------------------------------------------
    # RESULT
    # --------------------------------------------------------

    print()
    print("=" * 55)
    print("📈 NIFTY FUTURE")
    print("=" * 55)

    print(f"Symbol : {symbol}")
    print(f"Token  : {token}")
    print(f"PRICE  : {price:.2f}")

    print("=" * 55)
    print()


if __name__ == "__main__":
    main()
```
