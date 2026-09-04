```python
from runclntpxy import get_session
from datetime import datetime, timedelta


EXCHANGE_SEGMENT = "nse_fo"
UNDERLYING = "NIFTY"


def last_tuesday(year, month):
    """Return the last Tuesday of the given month."""

    if month == 12:
        next_month = datetime(year + 1, 1, 1)
    else:
        next_month = datetime(year, month + 1, 1)

    day = next_month - timedelta(days=1)

    while day.weekday() != 1:   # Tuesday
        day -= timedelta(days=1)

    return day


def get_current_month_expiry():
    """Return current month's expiry, or next month's if already expired."""

    now = datetime.now()

    expiry = last_tuesday(now.year, now.month)

    if now.date() > expiry.date():

        if now.month == 12:
            expiry = last_tuesday(now.year + 1, 1)
        else:
            expiry = last_tuesday(now.year, now.month + 1)

    return expiry


def get_nifty_future(session, expiry):
    """Find current-month NIFTY FUT from Kotak Neo."""

    response = session.search_scrip(
        exchange_segment=EXCHANGE_SEGMENT,
        symbol=UNDERLYING
    )

    if isinstance(response, list):
        results = response

    elif isinstance(response, dict):
        results = response.get("data", [])

        if isinstance(results, dict):
            results = [results]

    else:
        results = []

    if not results:
        return None, None

    month = expiry.strftime("%b").upper()
    year = expiry.strftime("%y")

    for item in results:

        if not isinstance(item, dict):
            continue

        symbol = str(
            item.get("pTrdSymbol") or ""
        ).upper()

        if (
            symbol == f"NIFTY{year}{month}FUT"
        ):
            return symbol, item.get("pSymbol")

    return None, None


def get_ltp(session, neo_symbol):
    """Get live LTP using Kotak Neo quotes API."""

    try:

        # Kotak Neo SDK quotes() accepts:
        # quotes(exchange_segment, instrument_tokens)

        response = session.quotes(
            EXCHANGE_SEGMENT,
            neo_symbol
        )

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

            if ltp is not None:
                return ltp

        return None

    except Exception as e:

        print("❌ Quote error:")
        print(e)

        return None


def main():

    print()
    print("=" * 50)
    print("PXY - NIFTY FUTURE LIVE PRICE")
    print("=" * 50)

    # --------------------------------------------------
    # LOGIN
    # --------------------------------------------------

    session = get_session()

    if session is None:
        print("❌ Login failed")
        return

    # --------------------------------------------------
    # EXPIRY
    # --------------------------------------------------

    expiry = get_current_month_expiry()

    print(f"Expiry : {expiry.strftime('%d-%b-%Y')}")
    print("Searching NIFTY...")
    print()

    # --------------------------------------------------
    # FIND FUTURE
    # --------------------------------------------------

    nifty_symbol, nifty_token = get_nifty_future(
        session,
        expiry
    )

    if nifty_symbol is None:

        print("❌ Current month NIFTY FUT not found")
        return

    print("✅ NIFTY FUT FOUND")
    print(f"Neo Symbol : {nifty_symbol}")
    print(f"pSymbol    : {nifty_token}")
    print()

    # --------------------------------------------------
    # LIVE PRICE
    # --------------------------------------------------

    ltp = get_ltp(
        session,
        nifty_symbol
    )

    if ltp is None:

        print("❌ LTP not available")
        return

    # --------------------------------------------------
    # OUTPUT
    # --------------------------------------------------

    print("=" * 50)
    print(f"NIFTY FUT : {nifty_symbol}")
    print(f"LIVE LTP  : {ltp}")
    print("=" * 50)


if __name__ == "__main__":
    main()
```
