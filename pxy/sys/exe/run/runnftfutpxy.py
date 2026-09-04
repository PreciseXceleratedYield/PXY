import calendar
import json
from datetime import datetime
# Import your authenticated session function from runclntpxy.py
from runclntpxy import get_session


def get_current_month_expiry_date():
    """Calculates the exact last Tuesday day integer for the current month

    and formats it to match Kotak's F&O string layout (e.g., '29SEP26').
    """
    today = datetime.today()
    year = today.year
    month = today.month

    # Generate calendar framework for the current month
    month_cal = calendar.monthcalendar(year, month)

    # Identify the last week list containing Tuesday (Index 1)
    if month_cal[-1][1] != 0:
        last_tuesday_day = month_cal[-1][1]
    else:
        last_tuesday_day = month_cal[-2][1]

    expiry_date_str = (
        f"{last_tuesday_day:02d}{today.strftime('%b').upper()}{str(year)[2:]}"
    )
    return expiry_date_str


def autodetect_and_get_quotes():
    print("Initializing session via runclntpxy...")
    session = get_session()

    if not session:
        print("Error: Authentication failed.")
        return

    print("Session authenticated successfully! ✅")

    # 1. Dynamically compute the contract string format
    detected_expiry = get_current_month_expiry_date()
    # For the fallback search matching index contracts
    target_pattern = f"NIFTY{detected_expiry}"

    print(f"Auto-detected current month expiry pattern: '{detected_expiry}'")

    token, ltp, trading_symbol = None, None, None

    try:
        # 2. Execute alternative extraction matrix directly via search_scrip
        # We query using "NIFTY" to pull the active futures contract mappings
        print("Querying active index scrip mappings from Kotak backend...")
        search_res = session.search_scrip(
            exchange_segment="nse_fo", symbol="NIFTY"
        )

        if search_res:
            # Handle if the response comes back wrapped or flat
            search_data = (
                search_res.get("data", search_res)
                if isinstance(search_res, dict)
                else search_res
            )
            if isinstance(search_data, dict):
                search_data = [search_data]

            if isinstance(search_data, list):
                for item in search_data:
                    # Scan all possible symbol column aliases used by Kotak SDK versions
                    symbol_name = str(
                        item.get("pSymbolName")
                        or item.get("pTrdSymbol")
                        or item.get("pSymbol")
                        or item.get("tsym")
                        or ""
                    ).upper()

                    # Match expiry string (e.g. '29SEP26') and look for the FUT designation
                    if detected_expiry in symbol_name and (
                        "FUT" in symbol_name
                        or not ("CE" in symbol_name or "PE" in symbol_name)
                    ):
                        token = (
                            item.get("pToken")
                            or item.get("tok")
                            or item.get("instrument_token")
                        )
                        trading_symbol = (
                            item.get("pSymbolName")
                            or item.get("pTrdSymbol")
                            or item.get("tsym")
                        )
                        break

        # 3. Request live market metrics if a valid numeric token was successfully isolated
        if token:
            print(f"Token resolved: {token}. Requesting market snapshot quotes...")
            numeric_payload = [
                {"instrument_token": str(token), "exchange_segment": "nse_fo"}
            ]
            fresh_quote = session.quotes(instrument_tokens=numeric_payload)

            if fresh_quote:
                fresh_data = (
                    fresh_quote.get("data", fresh_quote)
                    if isinstance(fresh_quote, dict)
                    else fresh_quote
                )

                if isinstance(fresh_data, list) and len(fresh_data) > 0:
                    instrument_feed = fresh_data[0]
                elif isinstance(fresh_data, dict):
                    # Unpack inner list arrays if present
                    inner_data = fresh_data.get("data", fresh_data)
                    instrument_feed = (
                        inner_data[0]
                        if isinstance(inner_data, list) and len(inner_data) > 0
                        else inner_data
                    )
                else:
                    instrument_feed = {}

                ltp = (
                    instrument_feed.get("ltp")
                    or instrument_feed.get("last_price")
                    or instrument_feed.get("pLastTradedPrice")
                )

        # 4. Display Results
        print("\n==============================")
        print(f"  SYMBOL : {trading_symbol if trading_symbol else 'NIFTY FUT'}")
        print(f"  TOKEN  : {token}")
        print(f"  LTP    : ₹ {ltp if ltp else 'None'}")
        print("==============================")

    except Exception as e:
        print(f"API Connection Exception: {e}")


if __name__ == "__main__":
    autodetect_and_get_quotes()
