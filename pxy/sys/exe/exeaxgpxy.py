from colorama import Fore

def send_market_order(client, symbol, qty, tag):
    """
    Handles isolated Kotak NeoAPI order placement.
    Returns True on success, False on failure.
    """
    try:
        params = {
            "exchange_segment": "nse_fo",
            "product": "NRML",
            "price": "0",
            "order_type": "MKT",
            "quantity": str(qty),
            "trading_symbol": str(symbol),
            "transaction_type": "B",
            "validity": "DAY",
            "amo": "NO",
            "tag": tag
        }
        res = client.place_order(**params)
        return bool(res)
    except Exception as e:
        print(f"{Fore.RED}❌ NeoAPI Transmission Error: {e}")
        return False
