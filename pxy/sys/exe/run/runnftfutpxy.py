from runclntpxy import get_session
from datetime import datetime, timedelta


EXCHANGE_SEGMENT = "nse_fo"


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

    expiry = last_tuesday(now.year, now.month)

    if now.date() > expiry.date():

        if now.month == 12:
            expiry = last_tuesday(now.year + 1, 1)
        else:
            expiry = last_tuesday(now.year, now.month + 1)

    return expiry


def main():

    print()
    print("=" * 50)
    print("PXY - NIFTY FUTURE LIVE PRICE")
    print("=" * 50)

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

    print(f"Expiry : {expiry.strftime('%d-%b-%Y')}")
    print("Searching NIFTY...")
    print()

    # --------------------------------------------------------
    # SEARCH NIFTY
    # --------------------------------------------------------

    response = session.search_scrip(
        exchange_segment=EXCHANGE_SEGMENT,
        symbol="NIFTY"
    )

    print("Search response:")
    print(response)
    print()

    # --------------------------------------------------------
    # NORMALIZE RESPONSE
    # --------------------------------------------------------

    if isinstance(response, list):

        results = response

    elif isinstance(response, dict):

        results = response.get("data", [])

        if isinstance(results, dict):
            results = [results]

    else:

        results = []

    if not results:

        print("❌ No NIFTY instruments found")
        return

    # --------------------------------------------------------
    # FIND FUTURE
    # --------------------------------------------------------

    month = expiry.strftime("%b").upper()
    year = expiry.strftime("%y")

    nifty_symbol = None

    for item in results:

        if not isinstance(item, dict):
            continue

        # Print fields so we know exactly what Kotak returns
        symbol = (
            item.get("pTrdSymbol")
            or item.get("pSymbol")
            or item.get("pSymbolName")
            or item.get("symbol")
            or item.get("tsym")
            or item.get("neo_symbol")
            or ""
        )

        symbol = str(symbol).upper()

        # Current month NIFTY future
        #
        # Example:
        # NIFTY26SEPFUT
        #
        if (
            symbol.startswith("NIFTY")
            and month in symbol
            and year in symbol
            and symbol.endswith("FUT")
        ):

            nifty_symbol = symbol
            break

    # --------------------------------------------------------
    # NOT FOUND
    # --------------------------------------------------------

    if nifty_symbol is None:

        print("❌ Current month NIFTY FUT not found")
        print()
        print("NIFTY candidates:")

        for item in results:

            if isinstance(item, dict):

                print(item)

        return

    # --------------------------------------------------------
    # FOUND
    # --------------------------------------------------------

    print("✅ NIFTY FUT FOUND")
    print(f"Neo Symbol : {nifty_symbol}")
    print()

    # --------------------------------------------------------
    # GET LIVE QUOTE
    # --------------------------------------------------------

    try:

        quote = session.quotes(
            exchange_segment=EXCHANGE_SEGMENT,
            instrument_tokens=nifty_symbol,
            quote_type="ltp"
        )

    except Exception as e:

        print("❌ Quote error:")
        print(e)
        return

    # --------------------------------------------------------
    # DISPLAY
    # --------------------------------------------------------

    print("Quote response:")
    print(quote)
    print()

    # --------------------------------------------------------
    # FIND LTP
    # --------------------------------------------------------

    ltp = None

    if isinstance(quote, dict):

        data = quote.get("data", quote)

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

    if ltp is not None:

        print("=" * 50)
        print(f"NIFTY FUT : {nifty_symbol}")
        print(f"LIVE LTP  : {ltp}")
        print("=" * 50)

    else:

        print("⚠️ LTP not found in response")


if __name__ == "__main__":
    main()
