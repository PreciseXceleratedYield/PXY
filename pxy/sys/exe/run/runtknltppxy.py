import sys
import os
import json
from pathlib import Path
from colorama import Fore, init

init(autoreset=True)

# --- PATH CONFIGURATION ---
HERE = Path(__file__).resolve().parent
REGISTRY_FILE = HERE / "tknregistry.json"
JSON_OUTPUT_FILE = HERE / "nftfut.json"

# Fix parent imports if needed to fetch session info seamlessly
if str(HERE.parent) not in sys.path:
    sys.path.append(str(HERE.parent))
if str(HERE.parent.parent) not in sys.path:
    sys.path.append(str(HERE.parent.parent))

try:
    from runclntpxy import get_session
except Exception as imp_err:
    print(f"{Fore.RED}❌ IMPORT ERROR in runtknltppxy.py: {imp_err}")
    sys.exit(1)

# --- SEARCH RESULT NORMALIZATION ---
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

# --- CORE CACHE ENGINE ---
def get_ltp_by_symbol(client, symbol: str, segment: str = "nse_fo") -> float:
    symbol = symbol.upper().strip()
    token_mapping = {}
    token = None

    # 1. Read existing token cache from disk if available
    if REGISTRY_FILE.exists():
        try:
            with open(REGISTRY_FILE, "r", encoding="utf-8") as f:
                token_mapping = json.load(f)
        except Exception:
            token_mapping = {}

    token = token_mapping.get(symbol)

    # 2. Cache Validation & Resolution Routing Gate
    if token:
        print(f"{Fore.GREEN}🎯 [CACHE HIT] {symbol} -> Token: {token}")
    else:
        print(f"{Fore.YELLOW}⚡ [CACHE MISS] Searching broker scrip master for {symbol}...")
        try:
            response = client.search_scrip(exchange_segment=segment, symbol=symbol)
            results = normalize_results(response)

            # CRITICAL FIX: Enforce exact string match matching Kotak Neo payload schemas
            for row in results:
                if not isinstance(row, dict):
                    continue
                
                # Check Kotak Neo native trading symbol structure parameters
                found_sym = str(row.get("pTrdSymbol") or row.get("trading_symbol") or "").upper().strip()
                
                # Rigid guard checking: Skips partial/futures matches to prevent token contamination
                if found_sym == symbol:
                    token = str(row.get("pSymbol") or row.get("token") or "").strip()
                    break

            # 3. Commit found token signature to disk registry
            if token:
                token_mapping[symbol] = token
                with open(REGISTRY_FILE, "w", encoding="utf-8") as f:
                    json.dump(token_mapping, f, indent=4)
                print(f"{Fore.GREEN}💾 [CACHE WRITE] Saved {symbol} -> Token {token}")
            else:
                print(f"{Fore.RED}❌ [SEARCH ERROR] Symbol '{symbol}' could not be resolved from master contract list.")
                return 0.0

        except Exception as e:
            print(f"{Fore.RED}💥 [SEARCH EXCEPTION] Lookups broke for symbol {symbol}: {e}")
            return 0.0

    # 4. Pull Live Market Data via Working Quotes System
    try:
        # Construct the unique instrumentation array required by Kotak Neo
        instr = [{"instrument_token": str(token), "exchange_segment": segment}]
        res = client.quotes(instrument_tokens=instr, quote_type="ltp")

        if not res or not isinstance(res, list) or len(res) == 0:
            print(f"{Fore.RED}❌ [QUOTE ERROR] Broker returned empty data list.")
            return 0.0

        # Extract context block from indices list
        data = res[0] if isinstance(res, list) else res
        
        # Pull live contract valuation fields from dictionary payload 
        price = float(data.get("ltp") or data.get("last_price") or 0.0)
        
        # Commit context values back to target update frame file
        if price > 0:
            with open(JSON_OUTPUT_FILE, "w", encoding="utf-8") as f:
                json.dump({"price": price}, f, indent=4)
        return price
        
    except Exception as quote_err:
        print(f"{Fore.RED}💥 [QUOTE EXCEPTION] Quotes query breakdown for token {token}: {quote_err}")
        return 0.0

# --- RUNNER INTERFACE ---
def main():
    if len(sys.argv) < 2:
        print(f"{Fore.RED}⚠️ Missing Symbol Parameter! Usage: python3 runtknltppxy.py <SYMBOL>")
        return

    target_symbol = sys.argv[1].strip()
    client = get_session()
    if not client:
        print(f"{Fore.RED}❌ Failed to acquire client session frame.")
        return

    price = get_ltp_by_symbol(client, target_symbol)
    if price > 0:
        print(f"{Fore.CYAN}📈 {target_symbol} premium trading at {price:.2f}")
    else:
        print(f"{Fore.RED}❌ Failed to resolve options premium market price.")

if __name__ == "__main__":
    main()

