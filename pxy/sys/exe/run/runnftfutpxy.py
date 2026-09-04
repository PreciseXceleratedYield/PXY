from runclntpxy import get_session

def get_nifty_sep_token():
    session = get_session()
    if not session:
        print("❌ Authentication Failed.")
        return

    try:
        # Querying the scrip master database for Kotak Neo
        search_result = session.search_scrip(
            exchange_segment="nse_fo", 
            symbol="NIFTY26SEPFUT",
            expiry="24SEP2026",
            option_type="X",
            strike_price="0"
        )
        
        # Fallback query pattern if the explicit payload returns empty
        if not search_result or 'data' not in search_result or len(search_result['data']) == 0:
            search_result = session.search_scrip(
                exchange_segment="nse_fo", 
                symbol="NIFTY26SEPFUT",
                expiry="24SEP2026",
                option_type="",
                strike_price=""
            )

        if not search_result or 'data' not in search_result or len(search_result['data']) == 0:
            print("❌ Contract row not found.")
            return

        # Extract the dictionary container dynamically
        data_block = search_result['data']
        scrip_data = data_block[0] if isinstance(data_block, list) else data_block
        
        # Check all possible dictionary key variants used by Kotak APIs
        token = scrip_data.get("instrument_token") or scrip_data.get("pSymbolToken") or scrip_data.get("pToken")
        symbol = scrip_data.get("trading_symbol") or scrip_data.get("pTrdSym")
        
        print(f"Symbol: {symbol} | Token: {token}")
        return token

    except Exception as e:
        print(f"❌ Error finding token: {e}")

if __name__ == "__main__":
    get_nifty_sep_token()



