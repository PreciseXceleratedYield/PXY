
from runclntpxy import get_session
from datetime import datetime, timedelta
import csv
import os


EXCHANGE_SEGMENT = "nse_fo"
SEARCH_SYMBOL = "NIFTY"

CSV_FILE = "nifty_search.csv"


# ============================================================
# LAST TUESDAY
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


# ============================================================
# CURRENT MONTH EXPIRY
# ============================================================

def get_current_month_expiry():

    now = datetime.now()

    expiry = last_tuesday(
        now.year,
        now.month
    )

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
# NORMALIZE SEARCH RESPONSE
# ============================================================

def normalize_results(response):

    if isinstance(response, list):
        return response

    if isinstance(response, dict):

        data = response.get("data", [])

        if isinstance(data, dict):
            return [data]

        if isinstance(data, list):
            return data

    return []


# ============================================================
# DUMP SEARCH RESPONSE TO CSV
# ============================================================

def dump_to_csv(results):

    if not results:
        return

    # Collect every field returned by Kotak
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

    print(f"💾 Search data dumped : {CSV_FILE}")
    print(f"📊 Records            : {len(results)}")


# ============================================================
# FIND NIFTY FUTURE
# ============================================================

def find_nifty_future(results, expiry):

    month = expiry.strftime("%b").upper()
    year = expiry.strftime("%y")

    expected_symbol = f"NIFTY{year}{month}FUT"

    print()
    print(f"Looking for : {expected_symbol}")
    print()

    for item in results:

        if not isinstance(item, dict):
            continue

        symbol = str(
            item.get("pTrdSymbol") or ""
        ).upper()

        if symbol == expected_symbol:

            token = item.get("pSymbol")

            return symbol, token, item

    return None, None, None


# ============================================================
# GET LTP
# ============================================================

def get_ltp(session, token):

    try:

        # IMPORTANT:
        # Kotak Neo quotes expects the exchange segment
        # and instrument token list.

        response = session.quotes(
            EXCHANGE_SEGMENT,
            [str(token)]
        )

        print()
        print("Quote response:")
        print(response)
        print()

        if not isinstance(response, dict):
            return None

        data = response.get("data")

        if isinstance(data, list) and data:
            data = data[0]

        if isinstance(data, dict):

            ltp = (
                data.get("ltp")
                or data.get("LTP")
                or data.get("last_price")
                or data.get("pLtp")
                or data.get("pLastPrice")
            )

            return ltp

        return None

    except Exception as e:

        print("❌ Quote error:")
        print(e)

        return None


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

    session = get_session()

    if session is None:

        print("❌ Login failed")
        return

    # --------------------------------------------------------
    # EXPIRY
    # --------------------------------------------------------

    expiry = get_current_month_expiry()

    print(
        f"Expiry : {expiry.strftime('%d-%b-%Y')}"
    )

    print("Searching NIFTY...")
    print()

    # --------------------------------------------------------
    # SEARCH
    # --------------------------------------------------------

    try:

        response = session.search_scrip(
            exchange_segment=EXCHANGE_SEGMENT,
            symbol=SEARCH_SYMBOL
        )

    except Exception as e:

        print("❌ Search error:")
        print(e)
        return

    results = normalize_results(response)

    if not results:

        print("❌ No search results")
        return

    print(
        f"✅ Search results : {len(results)}"
    )

    # --------------------------------------------------------
    # DUMP EVERYTHING
    # --------------------------------------------------------

    dump_to_csv(results)

    # --------------------------------------------------------
    # FIND CURRENT MONTH FUT
    # --------------------------------------------------------

    nifty_symbol, nifty_token, nifty_data = (
        find_nifty_future(
            results,
            expiry
        )
    )

    if nifty_symbol is None:

        print()
        print("❌ NIFTY FUT not found")
        print(
            f"Expected : NIFTY"
            f"{expiry.strftime('%y%b').upper()}"
            f"FUT"
        )

        return

    print("=" * 55)
    print("✅ NIFTY FUT FOUND")
    print("=" * 55)

    print(f"Neo Symbol : {nifty_symbol}")
    print(f"pSymbol    : {nifty_token}")

    # --------------------------------------------------------
    # PRINT COMPLETE FUT ROW
    # --------------------------------------------------------

    print()
    print("Future instrument data:")

    for key, value in nifty_data.items():

        print(
            f"{key:<20} : {value}"
        )

    # --------------------------------------------------------
    # TOKEN CHECK
    # --------------------------------------------------------

    if nifty_token is None:

        print()
        print("❌ pSymbol/token missing")
        return

    # --------------------------------------------------------
    # LIVE QUOTE
    # --------------------------------------------------------

    ltp = get_ltp(
        session,
        nifty_token
    )

    if ltp is None:

        print("❌ LTP not found")
        return

    # --------------------------------------------------------
    # FINAL OUTPUT
    # --------------------------------------------------------

    print()
    print("=" * 55)
    print(f"NIFTY FUT : {nifty_symbol}")
    print(f"TOKEN     : {nifty_token}")
    print(f"LIVE LTP  : {ltp}")
    print("=" * 55)


if __name__ == "__main__":
    main()
```
