import sys
import asyncio
from pathlib import Path
from datetime import datetime, time
import pytz
from colorama import Fore, init, Style
import traceback

# --- GLOBAL DEBUG SWITCH ---
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

        dprint(f"ORDER: {symbol} QTY={qty}", Fore.YELLOW)
        res = client.place_order(**params)
        return {"stat": "OK" if res else "FAIL", "raw": res}

    except Exception as e:
        return {"stat": "FAIL", "err": str(e)}


# --- MAIN ---
async def main():
    try:
        IST = pytz.timezone("Asia/Kolkata")
        now = datetime.now(IST).time()

        # --- MARKET SAFETY WINDOW ---
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
            print("❌ No market data")
            return

        entry_signal, reversal = get_entry_signal(df)
        sig = (entry_signal or "").upper().strip()

        valid = ["ATMBUY", "OTMBUY", "ATMSELL", "OTMSELL"]
        if sig not in valid:
            print(f"WAIT SIGNAL: {entry_signal}")
            return

        ltp = df["Close"].iloc[-1]

        # --- SYMBOL BUILD (ONLY ONCE) ---
        symbol = get_symbol(ltp, sig)
        if not symbol or symbol == "NA":
            print("❌ Symbol build failed")
            return

        # --- POSITION SAFETY ---
        try:
            pos = get_position_summary(client)
            ce_active = "1CE" in pos
            pe_active = "1PE" in pos
        except Exception:
            # SAFE MODE: assume positions exist if check fails
            ce_active = True
            pe_active = True
            pos = "UNKNOWN (SAFE MODE)"

        BUY_SIGS = ["ATMBUY", "OTMBUY"]
        SELL_SIGS = ["ATMSELL", "OTMSELL"]

        res = {"stat": "SKIPPED"}

        # --- TRADE DECISION (SIGNAL ONLY DRIVES IT) ---
        if sig in BUY_SIGS:
            if not ce_active:
                print(f"🚀 BUY CE: {symbol}")
                res = execute_order(client, symbol, LOT_SIZE)
            else:
                print("CE already active → SKIP SAFE")

        elif sig in SELL_SIGS:
            if not pe_active:
                print(f"🚀 BUY PE: {symbol}")
                res = execute_order(client, symbol, LOT_SIZE)
            else:
                print("PE already active → SKIP SAFE")

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
            print("❌ Main error (enable DEBUG)")


if __name__ == "__main__":
    asyncio.run(main())
