import os
import json
from colorama import Fore

# File where token mappings will be permanently stored
TOKEN_CACHE_FILE = "token_cache.json"

def get_generic_ltp(client, symbol: str, segment: str = "nse_fo") -> float:
    """
    Retrieves the LTP for any given trading symbol.
    Caches symbol-to-token mappings in a local JSON file to eliminate repetitive search API calls.
    """
    symbol = symbol.upper().strip()
    token_mapping = {}

    # 1. Read existing cache if available
    if os.path.exists(TOKEN_CACHE_FILE):
        try:
            with open(TOKEN_CACHE_FILE, "r", encoding="utf-8") as f:
                token_mapping = json.load(f)
        except Exception:
            token_mapping = {}

    # 2. Check if the token is already cached
    token = token_mapping.get(symbol)

    if token:
        print(f"{Fore.GREEN}🎯 [CACHE HIT] Found Token {token} for {symbol}. Skipping search API.")
    else:
        print(f"{Fore.YELLOW}⚡ [CACHE MISS] Searching broker contract master for {symbol}...")
        try:
            # Reusing your exact search method format
            response = client.search_scrip(exchange_segment=segment, symbol=symbol)
            
            # Reusing your exact normalize logic block
            results = []
            if isinstance(response, list):
                results = response
            elif isinstance(response, dict):
                data = response.get("data", [])
                if isinstance(data, list):
                    results = data
                elif isinstance(data, dict):
                    results = [data]

            # Scan results for an exact trading symbol match
            for row in results:
                if not isinstance(row, dict):
                    continue
                
                # Check both pTrdSymbol and traditional key flags depending on instrument type
                found_sym = str(row.get("pTrdSymbol") or row.get("trading_symbol") or "").upper().strip()
                
                if found_sym == symbol:
                    token = str(row.get("pSymbol") or row.get("token") or "").strip()
                    break

            # If found, save it to our persistent disk file
            if token:
                token_mapping[symbol] = token
                with open(TOKEN_CACHE_FILE, "w", encoding="utf-8") as f:
                    json.dump(token_mapping, f, indent=4)
                print(f"{Fore.GREEN}💾 [CACHE WRITE] Saved {symbol} -> Token {token} to registry file.")
            else:
                print(f"{Fore.RED}❌ [CACHE ERROR] Symbol '{symbol}' not found in search results.")
                return 0.0

        except Exception as e:
            print(f"{Fore.RED}💥 [CACHE ERROR] Failed during scrip discovery phase: {e}")
            return 0.0

    # 3. Pull Live Market Data using your exact working quotes function logic
    try:
        instr = [{"instrument_token": str(token), "exchange_segment": segment}]
        res = client.quotes(instrument_tokens=instr, quote_type="ltp")

        if not res or not isinstance(res, list) or len(res) == 0:
            return 0.0

        data = res[0] if isinstance(res, list) else res
        return float(data.get("ltp") or data.get("last_price") or 0.0)
        
    except Exception:
        return 0.0
