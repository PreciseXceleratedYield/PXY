import sys
import os
import json
import re
from pathlib import Path
from colorama import Fore, init

init(autoreset=True)

# --- PATH CONFIGURATION ---
HERE = Path(__file__).resolve().parent
REGISTRY_FILE = HERE / "tknregistry.json"
JSON_OUTPUT_FILE = HERE / "nftopt.json"

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

# --- CORE OPTIONS ENGINE ---
def get_ltp_by_symbol(client, symbol: str, segment: str = "nse_fo") -> float:
    symbol = symbol.upper().strip()
    
    # STRICT BLOCK: Reject any string that does not end with CE or PE
    if not re.search(r'(CE|PE)$', symbol):
        print(f"{Fore.RED}❌ [SECURITY BLOCK] {symbol} rejected! This script only processes CE or PE options.")
        return 0.0

    token_mapping = {}
    token = None

    if REGISTRY_FILE.exists():
        try:
            with open(REGISTRY_FILE, "r", encoding="utf-8") as f:
                token_mapping = json.load(f)
        except Exception:
            token_mapping = {}

    token = token_mapping.get(symbol)

    # Cache Gateway Check
    if token:
        print(f"{Fore.GREEN}🎯 [OPTIONS CACHE HIT] {symbol} -> Token: {token}")
    else:
        print(f"{Fore.YELLOW}⚡ [OPTIONS CACHE MISS] Querying master options scrip for {symbol}...")
        try:
            response = client.search_scrip(exchange_segment=segment, symbol=symbol)
            results = normalize_results(response)

            for row in results:
                if not isinstance(row, dict):
                    continue
                
                found_sym = str(row.get("pTrdSymbol") or row.get("trading_symbol") or "").upper().strip()
                
                # Rigid Equality Matching Guard
                if found_sym == symbol:
                    token = str(row.get("pSymbol") or row.get("token") or "").strip()
                    break

            if token:
                token_mapping[symbol] = token
                with open(REGISTRY_FILE, "w", encoding="utf-8") as f:
                    json.dump(token_mapping, f, indent=4)
                print(f"{Fore.GREEN}💾 [OPTIONS CACHE WRITE] Registered {symbol} -> Token {token}")
            else:
                print(f"{Fore.RED}❌ [OPTIONS SEARCH ERROR] Option contract '{symbol}' not found in master contract list.")
                return 0.0

        except Exception as e:
            print(f"{Fore.RED}💥 [OPTIONS SEARCH EXCEPTION] Lookup broke for option {symbol}: {e}")
            return 0.0

    # Live Valuation Retrieval Block
    try:
        instr = [{"instrument_token": str(token), "exchange_segment": segment}]
        res = client.quotes(instrument_tokens=instr, quote_type="ltp")

        if not res or not isinstance(res, list) or len(res) == 0:
            print(f"{Fore.RED}❌ [OPTIONS QUOTE ERROR] Broker data array empty.")
            return 0.0

        # Kotak Neo structures lists directly or wraps inside list matrices
        data = res[0] if isinstance(res, list) else res
        price = float(data.get("ltp") or data.get("last_price") or 0.0)
        
        # Overwrite option price context payload to file
        if price > 0:
            with open(JSON_OUTPUT_FILE, "w", encoding="utf-8") as f:
                json.dump({"price": price}, f, indent=4)
        return price
        
    except Exception as quote_err:
        print(f"{Fore.RED}💥 [OPTIONS QUOTE EXCEPTION] Query breakdown for token {token}: {quote_err}")
        return 0.0

def main():
    if len(sys.argv) < 2:
        print(f"{Fore.RED}⚠️ Missing Symbol! Usage: python3 runtknltppxy.py <OPTIONS_SYMBOL>")
        return

    # FIXED: Added index parameter index location array assignment [1]
    target_symbol = sys.argv[1].strip()
    
    client = get_session()
    if not client:
        print(f"{Fore.RED}❌ Failed to acquire client trading session frame.")
        return

    price = get_ltp_by_symbol(client, target_symbol)
    if price > 0:
        print(f"{Fore.CYAN}📈 {target_symbol} premium trading at {price:.2f}")

if __name__ == "__main__":
    main()
