from runclntpxy import get_session
from datetime import datetime, timedelta


# ============================================================
# CONFIG
# ============================================================

EXCHANGE_SEGMENT = "nse_fo"
SEARCH_SYMBOL = "NIFTY"


# ============================================================
# GET LAST TUESDAY OF MONTH
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


# ============================================================
# CURRENT MONTH EXPIRY
# ============================================================

def get_expiry():

    now = datetime.now()

    expiry = last_tuesday(now.year, now.month)

    # If expiry has already passed, use next month
    if now.date() > expiry.date():

        if now.month == 12:
            expiry = last_tuesday(now.year + 1, 1)
        else:
            expiry = last_tuesday(now.year, now.month + 1)

    return expiry


# ============================================================
# MAIN
# ============================================================

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

    expiry = get_expiry()

    print(f"Expiry : {expiry.strftime('%d-%b-%Y')}")
    print("Searching NIFTY...")
    print()

    # --------------------------------------------------------
    # SEARCH
    # --------------------------------------------------------

    response = session.search_scrip(
        exchange_segment=EXCHANGE_SEGMENT,
        symbol=SEARCH_SYMBOL
    )

    # Kotak can return a LIST
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
        print(response)
        return

    # --------------------------------------------------------
    # FIND FUTURE
    # --------------------------------------------------------

    expiry_str = expiry.strftime("%d%b%y").upper()

    found_symbol = None
    found_token = None

    for item in results:

        if not isinstance(item, dict):
            continue

        # Try common Kotak fields
        symbol = str(
            item.get("pTrdSymbol")
            or item.get("pSymbol")
            or item.get("symbol")
            or item.get("tsym")
            or ""
        ).upper()

        instrument = str(
            item.get("pInstrumentName")
            or item.get("instrument")
            or ""
        ).upper()

        expiry_value = str(
            item.get("pExpiryDate")
            or item.get("expiry")
            or ""
        ).upper()

        token = (
            item.get("pToken")
            or item.get("token")
            or item.get("tok")
            or item.get("instrument_token")
        )

        text = f"{symbol} {instrument} {expiry_value}"

        # NIFTY + FUT
        if "NIFTY" not in text:
            continue

        if "FUT" not in text:
            continue

        # Current month
        if (
            expiry_str in text
            or expiry.strftime("%b").upper() in text
            and expiry.strftime("%y") in text
        ):

            found_symbol = symbol
            found_token = str(token)

            break

    # --------------------------------------------------------
    # NOT FOUND
    # --------------------------------------------------------

    if not found_symbol:

        print("❌ Current month NIFTY FUT not found")
        print()
        print("Available NIFTY results:")

        for item in results:

            if isinstance(item, dict):

                symbol = (
                    item.get("pTrdSymbol")
                    or item.get("pSymbol")
                    or item.get("symbol")
                    or item.get("tsym")
                    or ""
                )

                print(" ", symbol)

        print()
        return

    # --------------------------------------------------------
    # FOUND
    # --------------------------------------------------------

    print("✅ NIFTY FUT FOUND")
    print(f"Symbol : {found_symbol}")
    print(f"Token  : {found_token}")
    print()

    # --------------------------------------------------------
    # GET LIVE PRICE
    # --------------------------------------------------------

    try:

        quote = session.quotes(
            instrument_tokens=[
                {
                    "exchange_segment": EXCHANGE_SEGMENT,
                    "instrument_token": found_token
                }
            ],
            quote_type="ltp"
        )

    except Exception as e:

        print("❌ Quote error:")
        print(e)
        return

    # --------------------------------------------------------
    # DISPLAY RESPONSE
    # --------------------------------------------------------

    print("Quote:")
    print(quote)
    print()

    # --------------------------------------------------------
    # EXTRACT LTP
    # --------------------------------------------------------

    ltp = None

    if isinstance(quote, dict):

        data = quote.get("data", quote)

        if isinstance(data, list) and data:
            data = data[0]

        if isinstance(data, dict):

            ltp = (
                data.get("ltp")
                or data.get("last_price")
                or data.get("pLtp")
                or data.get("pLastPrice")
                or data.get("LTP")
            )

    if ltp is not None:

        print("=" * 50)
        print(f"NIFTY FUT : {found_symbol}")
        print(f"LIVE LTP  : {ltp}")
        print("=" * 50)

    else:

        print("⚠️ LTP field not identified.")
        print("Check the Quote response above.")


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    main()
