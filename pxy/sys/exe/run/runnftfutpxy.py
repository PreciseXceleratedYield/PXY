import calendar
from datetime import datetime
from runclntpxy import get_session


def get_current_month_expiry():
    today = datetime.today()

    cal = calendar.monthcalendar(today.year, today.month)

    # Last Tuesday
    expiry_day = next(
        week[calendar.TUESDAY]
        for week in reversed(cal)
        if week[calendar.TUESDAY] != 0
    )

    return f"{expiry_day:02d}{today.strftime('%b').upper()}{str(today.year)[2:]}"


def get_nifty_future_price():

    session = get_session()

    if not session:
        print("❌ Authentication failed")
        return

    expiry = get_current_month_expiry()
    target = f"NIFTY{expiry}"

    print(f"Searching: {target}")

    response = session.search_scrip(
        exchange_segment="nse_fo",
        symbol="NIFTY"
    )

    data = response.get("data", response)

    if isinstance(data, dict):
        data = [data]

    token = None
    symbol = None

    for item in data:

        tsym = str(
            item.get("pSymbolName")
            or item.get("pTrdSymbol")
            or item.get("tsym")
            or ""
        ).upper()

        # Current-month NIFTY FUT only
        if target in tsym and "CE" not in tsym and "PE" not in tsym:

            symbol = (
                item.get("pSymbolName")
                or item.get("pTrdSymbol")
                or item.get("tsym")
            )

            token = (
                item.get("pToken")
                or item.get("tok")
                or item.get("instrument_token")
            )

            break

    if not token:
        print(f"❌ {target} FUT not found")
        return

    quote = session.quotes(
        instrument_tokens=[
            {
                "instrument_token": str(token),
                "exchange_segment": "nse_fo"
            }
        ]
    )

    quote_data = quote.get("data", quote)

    if isinstance(quote_data, list):
        quote_data = quote_data[0]

    ltp = (
        quote_data.get("ltp")
        or quote_data.get("last_price")
        or quote_data.get("pLastTradedPrice")
    )

    print()
    print("==============================")
    print(f"SYMBOL : {symbol}")
    print(f"TOKEN  : {token}")
    print(f"LTP    : ₹ {ltp}")
    print("==============================")


if __name__ == "__main__":
    get_nifty_future_price()
