import sys
import asyncio
from pathlib import Path
from datetime import datetime, time
import pytz
from colorama import Fore, init, Style
import traceback

# --- GLOBAL CONFIG ---
DEBUG = True  # Set to True for detailed logs
COUNTERBUY = "NO" # Set to "YES" only if you want the Exit Regime to override signals
init(autoreset=True)

# --- PATH SETUP ---
HERE = Path(__file__).resolve().parent
PARENT = HERE.parent
for p in [HERE, HERE / "run", PARENT]:
    if str(p) not in sys.path:
        sys.path.append(str(p))

from syscnfgpxy import TICKER

# --- LOT SIZE LOGIC ---
t = TICKER.upper().strip()
if t == "^NSEBANK": LOT_SIZE = 30
elif t == "^NSEI": LOT_SIZE = 65
else: LOT_SIZE = None

# --- IMPORTS ---
def dprint(msg, color=Fore.CYAN):
    if DEBUG:
        print(f"{Style.BRIGHT}{color}[DEBUG] {msg}{Style.RESET_ALL}")

dprint("IMPORTING MODULES...")
try:
    from syspxy import get_all_data
    from runclntpxy import get_session
    from runfundpxy import get_available_funds
    from runpchkpxy import get_position_summary
    from runsymbpxy import get_symbol
    dprint("IMPORTS SUCCESS", Fore.GREEN)
except Exception as e:
    print(f"{Fore.RED}IMPORT ERROR: {e}")
    sys.exit(1)

# --- ORDER EXECUTION ---
def execute_order(client, symbol, qty):
    dprint(f"ENTER execute_order for {symbol}")
    try:
        params = {
            "exchange_segment": "nse_fo", "product": "NRML", "price": "0",
            "order_type": "MKT", "quantity": str(qty), "validity": "DAY",
            "trading_symbol": symbol, "transaction_type": "B", "amo": "NO",
            "disclosed_quantity": "0", "market_protection": "0"
        }
        dprint(f"ORDER PARAMS: {params}", Fore.YELLOW)
        res = client.place_order(**params)
        dprint(f"ORDER RESPONSE: {res}", Fore.GREEN)
        return {"stat": "OK" if res and str(res).strip() else "FAIL", "raw": res}
    except Exception as e:
        dprint(f"ORDER ERROR: {e}", Fore.RED)
        return {"stat": "FAIL", "err": str(e)}

async def main():
    dprint("===== MAIN START =====", Fore.GREEN)
    try:
        IST = pytz.timezone("Asia/Kolkata")
        now = datetime.now(IST).time()
        dprint(f"TIME CHECK: {now}")

        # --- MARKET BUFFER ---
        if (time(9, 14) <= now < time(9, 16)) or (time(15, 19) <= now < time(15, 31)):
            dprint("MARKET BUFFER ACTIVE - SKIPPING", Fore.YELLOW)
            return

        # --- SESSION ---
        client = get_session()
        if not client:
            print("❌ Session failed")
            return

        # --- DATA FETCH ---
        dprint("GETTING DATA FROM SYSPXY...")
        data = get_all_data()
        entry_signal = data.get("entry")
        reversal = data.get("exit") # Needed for Regime check
        ltp = data.get("price")

        # --- OTM DISTANCE ---
        try:
            TO, YC = int(float(data.get("TO"))), int(float(data.get("YC")))
            OTM_DISTANCE = (round(abs(TO - YC) / 100) * 100) * 2
            dprint(f"OTM_DYNAMIC: |{TO}-{YC}| * 2 = {OTM_DISTANCE}")
        except Exception as e:
            dprint(f"OTM fallback: {e}", Fore.YELLOW)
            OTM_DISTANCE = 100

        if not entry_signal:
            print("WAIT SIGNAL: None")
            return

        # --- SIGNAL NORMALIZATION ---
        sig = entry_signal.upper().strip()
        if sig == "STBUY": sig = "ATMBUY"
        elif sig == "STSELL": sig = "ATMSELL"
        
        VALID = ["ATMBUY", "OTMBUY", "ATMSELL", "OTMSELL"]
        if sig not in VALID:
            dprint(f"NON-TRADE SIGNAL: {sig}", Fore.YELLOW)
            return

        # --- POSITION AWARENESS (1:1 RATIO) ---
        dprint("CHECKING ACTUAL POSITION LOTS...")
        try:
            pos_summary = get_position_summary(client) # Expected "XCEYPE"
            parts = pos_summary.split("CE")
            ce_qty = int(parts[0])
            pe_qty = int(parts[1].replace("PE", ""))
            dprint(f"📊 LIVE RATIO -> CE:{ce_qty} | PE:{pe_qty}", Fore.MAGENTA)
        except Exception as e:
            print(f"{Fore.RED}❌ POSITION ERROR: {e}. Aborting.")
            return

        # --- REGIME CHECK (RE-IMPLEMENTED BUT BYPASSABLE) ---
        exit_sig = str(reversal).upper().strip() if reversal else "NONE"
        dprint(f"EXIT REGIME: {exit_sig} | ENTRY SIG: {sig}")
        
        if COUNTERBUY.upper() == "YES":
            dprint("COUNTERBUY ACTIVE: Logic would override here...", Fore.YELLOW)
            # (Regime correction logic would go here if needed)

        # --- FINAL EXECUTION BRANCHES ---
        BUY_SIGS = ["ATMBUY", "OTMBUY"]
        SELL_SIGS = ["ATMSELL", "OTMSELL"]
        symbol = None
        res = {"stat": "SKIPPED"}

        # CASE 1: BUY CE
        if sig in BUY_SIGS:
            dprint("BRANCH: ATTEMPT CE BUY")
            if (ce_qty == 0 and pe_qty == 0) or (ce_qty < pe_qty):
                dprint("⚖️ RATIO OK: Proceeding to buy CE...", Fore.GREEN)
                symbol = get_symbol(ltp, sig, OTM_DISTANCE)
                if symbol and symbol != "NA":
                    res = execute_order(client, symbol, LOT_SIZE)
                else: print("❌ CE symbol failed")
            else:
                print(f"✋ BLOCK CE: Already Balanced/Heavy ({ce_qty}:{pe_qty})")

        # CASE 2: BUY PE
        elif sig in SELL_SIGS:
            dprint("BRANCH: ATTEMPT PE BUY")
            if (ce_qty == 0 and pe_qty == 0) or (pe_qty < ce_qty):
                dprint("⚖️ RATIO OK: Proceeding to buy PE...", Fore.GREEN)
                symbol = get_symbol(ltp, sig, OTM_DISTANCE)
                if symbol and symbol != "NA":
                    res = execute_order(client, symbol, LOT_SIZE)
                else: print("❌ PE symbol failed")
            else:
                print(f"✋ BLOCK PE: Already Balanced/Heavy ({ce_qty}:{pe_qty})")

        # --- FINAL SUMMARY ---
        dprint("FETCHING FUNDS FOR SUMMARY...")
        funds = get_available_funds(client)
        print(f"""
        =====================================
        💰 Cash   : {int(funds)}
        📦 Ratio  : {ce_qty}CE : {pe_qty}PE
        🎯 Signal : {entry_signal}
        🎫 Symbol : {symbol}
        📌 Status : {res.get('stat')}
        =====================================
        """)
        dprint("===== MAIN END =====", Fore.GREEN)

    except Exception:
        print(traceback.format_exc())

if __name__ == "__main__":
    asyncio.run(main())

