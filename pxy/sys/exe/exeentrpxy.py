import sys
import asyncio
from pathlib import Path
from datetime import datetime, time
import pytz
from colorama import Fore, init, Style
import traceback

# --- GLOBAL CONFIG ---
DEBUG = False
init(autoreset=True)

LOT_SIZE = 65

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
try:
    from sysdtafpxy import fetch_yf_data
    from sysentrpxy import get_entry_signal
    from runclntpxy import get_session
    from runfundpxy import get_available_funds
    from runpchkpxy import get_position_summary
    from runsymbpxy import get_symbol
except Exception as e:
    print(f"{Fore.RED}IMPORT ERROR: {e}")
    sys.exit(1)


# --- ORDER EXECUTION ---
def execute_order(client, symbol, qty):
    try:
        params = {
            "exchange_segment": "nse_fo",
            "product": "NRML",
            "price": "0",
            "order_type": "MKT",
            "quantity": str(qty),
            "validity": "DAY",
            "trading_symbol": symbol,
            "transaction_type": "B",
            "amo": "NO",
            "disclosed_quantity": "0",
            "market_protection": "0"
        }

        dprint(f"ORDER -> {symbol} | QTY={qty}", Fore.YELLOW)
        res = client.place_order(**params)

        return {
            "stat": "OK" if res and str(res).strip() else "FAIL",
            "raw": res
        }

    except Exception as e:
        return {"stat": "FAIL", "err": str(e)}


# --- MAIN ---
async def main():
    try:
        IST = pytz.timezone("Asia/Kolkata")
        now = datetime.now(IST).time()

        # --- MARKET BUFFER ---
        if (time(9, 14) <= now < time(9, 16)) or (time(15, 16) <= now < time(15, 31)):
            print("⏳ Market buffer time - skipped")
            return

        # --- SESSION ---
        client = get_session()
        if not client:
            print("❌ Session failed")
            return

        # --- DATA ---
        df = fetch_yf_data()
        if df is None or df.empty:
            print("❌ No data")
            return

        entry_signal, reversal = get_entry_signal(df)

        # --- SAFETY FIX 1: entry_signal guard ---
        if not entry_signal:
            print("WAIT SIGNAL: None")
            return

        sig = entry_signal.upper().strip()

        VALID = ["ATMBUY", "OTMBUY", "ATMSELL", "OTMSELL"]

        if sig not in VALID:
            print(f"WAIT SIGNAL: {entry_signal}")
            return

        ltp = df["Close"].iloc[-1]

        # --- SAFETY FIX 2: position parsing ---
        try:
            pos = get_position_summary(client)

            if isinstance(pos, (list, tuple, set)):
                ce_active = "1CE" in pos
                pe_active = "1PE" in pos

            elif isinstance(pos, dict):
                ce_active = pos.get("1CE", False)
                pe_active = pos.get("1PE", False)

            else:
                ce_active = "1CE" in str(pos)
                pe_active = "1PE" in str(pos)

        except Exception:
            ce_active = True
            pe_active = True
            pos = "UNKNOWN (SAFE MODE)"

        BUY_SIGS = ["ATMBUY", "OTMBUY"]
        SELL_SIGS = ["ATMSELL", "OTMSELL"]

        symbol = None
        res = {"stat": "SKIPPED"}

        # --- BUY CE ---
        if sig in BUY_SIGS:
            if ce_active:
                print("CE already active → SKIP")
            else:
                symbol = get_symbol(ltp, sig)
                if not symbol or symbol == "NA":
                    print("❌ CE symbol failed")
                    return

                print(f"🚀 BUY CE: {symbol}")
                res = execute_order(client, symbol, LOT_SIZE)

        # --- BUY PE ---
        elif sig in SELL_SIGS:
            if pe_active:
                print("PE already active → SKIP")
            else:
                symbol = get_symbol(ltp, sig)
                if not symbol or symbol == "NA":
                    print("❌ PE symbol failed")
                    return

                print(f"🚀 BUY PE: {symbol}")
                res = execute_order(client, symbol, LOT_SIZE)

        # --- FUNDS ---
        funds = get_available_funds(client)

        status = res.get("stat", "FAIL")

        print(f"""
=================================
    💰 Cash   : {int(funds)}
    📦 Pos    : {pos}
    🎫 Symbol : {symbol}
    🎯 Signal : {entry_signal}
    📌 Status : {status}
=================================
""")

    except Exception:
        if DEBUG:
            print(traceback.format_exc())
        else:
            print("❌ Main error")


if __name__ == "__main__":
    asyncio.run(main())
