import sys
import asyncio
from pathlib import Path
from datetime import datetime, time
import pytz
from colorama import Fore, init, Style
import traceback

# --- GLOBAL CONFIG ---
DEBUG = True
init(autoreset=True)

# --- ADD PARENT DIR TO PATH ---
HERE = Path(__file__).resolve().parent
PARENT = HERE.parent

if str(PARENT) not in sys.path:
    sys.path.append(str(PARENT))

# --- IMPORT CONFIG FROM PARENT DIR ---
from syscnfgpxy import TICKER

# --- LOT SIZE (EXACT MATCH LOGIC) ---
t = TICKER.upper().strip()

if t == "^NSEBANK":
    LOT_SIZE = 30
elif t == "^NSEI":
    LOT_SIZE = 65
else:
    LOT_SIZE = None

# --- PATH FIX ---
HERE = Path(__file__).resolve().parent
RUN_DIR = HERE / "run"

for p in [HERE, RUN_DIR, HERE.parent]:
    if str(p) not in sys.path:
        sys.path.append(str(p))

# --- DEBUG PRINT ---
def dprint(msg, color=Fore.CYAN):
    if DEBUG:
        print(f"{Style.BRIGHT}{color}[DEBUG] {msg}{Style.RESET_ALL}")

# --- IMPORTS ---
dprint("IMPORTING MODULES...")
try:
    from sysdtafpxy import fetch_yf_data
    from sysentrpxy import get_entry_signal
    from runclntpxy import get_session
    from runfundpxy import get_available_funds
    from runpchkpxy import get_position_summary
    from runsymbpxy import get_symbol
    dprint("IMPORTS SUCCESS")
except Exception as e:
    print(f"{Fore.RED}IMPORT ERROR: {e}")
    sys.exit(1)


# --- ORDER EXECUTION ---
def execute_order(client, symbol, qty):
    dprint("ENTER execute_order")
    try:
        params = {
            "exchange_segment": "nse_fo",
            "product": "NRML",
            "price": "0",
            "order_type": "L",
            "quantity": str(qty),
            "validity": "DAY",
            "trading_symbol": symbol,
            "transaction_type": "B",
            "amo": "YES",
            "disclosed_quantity": "0",
            "market_protection": "0"
        }


        dprint(f"ORDER PARAMS: {params}", Fore.YELLOW)

        res = client.place_order(**params)

        dprint(f"ORDER RESPONSE: {res}", Fore.GREEN)

        return {
            "stat": "OK" if res and str(res).strip() else "FAIL",
            "raw": res
        }

    except Exception as e:
        dprint(f"ORDER ERROR: {e}", Fore.RED)
        return {"stat": "FAIL", "err": str(e)}


# --- MAIN ---
async def main():
    dprint("===== MAIN START =====", Fore.GREEN)

    try:
        IST = pytz.timezone("Asia/Kolkata")
        now = datetime.now(IST).time()

        dprint(f"TIME CHECK: {now}")

        # --- MARKET BUFFER ---
        if (time(9, 14) <= now < time(9, 16)) or (time(15, 16) <= now < time(15, 31)):
            dprint("MARKET BUFFER ACTIVE - SKIPPING", Fore.YELLOW)
            print("⏳ Market buffer time - skipped")
            return

        # --- SESSION ---
        dprint("CREATING SESSION...")
        client = get_session()
        dprint(f"SESSION RESULT: {client}")

        if not client:
            print("❌ Session failed")
            return

        # --- DATA ---
        dprint("FETCHING DATA...")
        df = fetch_yf_data()
        dprint(f"DATA RECEIVED: {type(df)}")

        if df is None or df.empty:
            print("❌ No data")
            return

        dprint(f"DATA ROWS: {len(df)}")

        # --- SIGNAL ---
        dprint("GETTING ENTRY SIGNAL...")
        entry_signal, reversal = get_entry_signal(df)
        dprint(f"SIGNAL RAW: {entry_signal} | REVERSAL: {reversal}")

        if not entry_signal:
            print("WAIT SIGNAL: None")
            return

        sig = entry_signal.upper().strip()
        dprint(f"FORMATTED SIGNAL: {sig}")

        VALID = ["ATMBUY", "OTMBUY", "ATMSELL", "OTMSELL"]

        if sig not in VALID:
            print(f"WAIT SIGNAL: {entry_signal}")
            return

        ltp = df["Close"].iloc[-1]
        dprint(f"LTP: {ltp}")

        # --- POSITION CHECK ---
        dprint("CHECKING POSITIONS...")
        try:
            pos = get_position_summary(client)
            dprint(f"POSITION RAW: {pos}")

            if isinstance(pos, (list, tuple, set)):
                ce_active = "1CE" in pos
                pe_active = "1PE" in pos

            elif isinstance(pos, dict):
                ce_active = pos.get("1CE", False)
                pe_active = pos.get("1PE", False)

            else:
                ce_active = "1CE" in str(pos)
                pe_active = "1PE" in str(pos)

            dprint(f"CE_ACTIVE={ce_active}, PE_ACTIVE={pe_active}")

        except Exception as e:
            dprint(f"POSITION ERROR: {e}", Fore.RED)
            ce_active = True
            pe_active = True
            pos = "UNKNOWN (SAFE MODE)"

        BUY_SIGS = ["ATMBUY", "OTMBUY"]
        SELL_SIGS = ["ATMSELL", "OTMSELL"]

        symbol = None
        res = {"stat": "SKIPPED"}

        # --- BUY CE ---
        if sig in BUY_SIGS:
            dprint("BRANCH: BUY CE")

            if ce_active:
                dprint("CE ALREADY ACTIVE - SKIP", Fore.YELLOW)
                print("CE already active → SKIP")
            else:
                dprint("GETTING SYMBOL FOR CE...")
                symbol = get_symbol(ltp, sig)
                dprint(f"SYMBOL: {symbol}")

                if not symbol or symbol == "NA":
                    print("❌ CE symbol failed")
                    return

                print(f"🚀 BUY CE: {symbol}")
                dprint("EXECUTING ORDER CE...")
                res = execute_order(client, symbol, LOT_SIZE)

        # --- BUY PE ---
        elif sig in SELL_SIGS:
            dprint("BRANCH: BUY PE")

            if pe_active:
                dprint("PE ALREADY ACTIVE - SKIP", Fore.YELLOW)
                print("PE already active → SKIP")
            else:
                dprint("GETTING SYMBOL FOR PE...")
                symbol = get_symbol(ltp, sig)
                dprint(f"SYMBOL: {symbol}")

                if not symbol or symbol == "NA":
                    print("❌ PE symbol failed")
                    return

                print(f"🚀 BUY PE: {symbol}")
                dprint("EXECUTING ORDER PE...")
                res = execute_order(client, symbol, LOT_SIZE)

        # --- FUNDS ---
        dprint("FETCHING FUNDS...")
        funds = get_available_funds(client)
        dprint(f"FUNDS: {funds}")

        status = res.get("stat", "FAIL")

        dprint("FINAL SUMMARY PRINT")

        print(f"""
  =====================================
    💰 Cash   : {int(funds)}
    📦 Pos    : {pos}
    🎫 Symbol : {symbol}
    🎯 Signal : {entry_signal}
    📌 Status : {status}
  =====================================
""")

        dprint("===== MAIN END =====", Fore.GREEN)

    except Exception:
        if DEBUG:
            print(traceback.format_exc())
        else:
            print("❌ Main error")


if __name__ == "__main__":
    dprint("SCRIPT START")
    asyncio.run(main())
