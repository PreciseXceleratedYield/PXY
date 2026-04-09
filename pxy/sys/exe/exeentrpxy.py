import sys
import asyncio
from pathlib import Path
from datetime import datetime, time
import pytz
from colorama import Fore, init, Style
import math
import traceback

# --- GLOBAL DEBUG SWITCH ---
DEBUG = False  # Set False for production

init(autoreset=True)
LOT_SIZE = 65

# --- OFFSETS CONFIGURATION ---
OFFSET_ATM = 0        # ATM offset
OFFSET_OTM = 200      # OTM offset
OFFSET_SBEULYL = 300  # SBEULYL special case offset

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
except ImportError as e:
    print(f"{Fore.RED}❌ Critical Import Error: {e}")
    sys.exit(1)

# --- ROUNDING HELPERS ---
def round_up_50(x): return int(math.ceil(x / 50) * 50)
def round_down_50(x): return int(math.floor(x / 50) * 50)

# --- EXECUTE ORDER ---
def execute_order(client, symbol, qty, side):
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
        dprint(f"Executing Order for {symbol} | Params: {params}", Fore.YELLOW)
        res = client.place_order(**params)
        dprint(f"Order Response: {res}", Fore.GREEN)
        return res if res else {"stat": "Not_Ok", "errMsg": "No response from API"}
    except Exception as e:
        if DEBUG: dprint(f"Order Exception: {traceback.format_exc()}", Fore.RED)
        return {"stat": "Not_Ok", "errMsg": str(e)}

# --- MAIN ASYNC ---
async def main():
    try:
        IST = pytz.timezone("Asia/Kolkata")
        now = datetime.now(IST).time()
        dprint(f"Current IST Time: {now}")

        # --- Skip Windows ---
        skip_windows = [(time(9, 14), time(9, 16)), (time(15, 16), time(15, 31))]
        for start, end in skip_windows:
            if start <= now < end:
                dprint(f"Inside {start.strftime('%H:%M')} - {end.strftime('%H:%M')} buffer. Skipping execution.")
                return

        # --- Session & Market Data ---
        client = get_session()
        if not client:
            print(f"{Fore.RED}❌ Session failed")
            return

        df = fetch_yf_data()
        if df is None or df.empty:
            print(f"{Fore.RED}❌ No data from YF")
            return

        # --- Signals & Positions ---
        entry_signal, reversal = get_entry_signal(df)
        sig = entry_signal.upper().strip()
        ltp = df['Close'].iloc[-1]
        dprint(f"Raw Signal: {entry_signal} | Reversal: {reversal}")

        pos = get_position_summary(client)
        dprint(f"Current Positions: {pos}")
        ce_active, pe_active = "1CE" in pos, "1PE" in pos

        # --- SPECIAL CASE: SBEULYL ---
        if sig == "SBEULYL":
            ce_strike = round_up_50(ltp + OFFSET_SBEULYL)
            pe_strike = round_down_50(ltp - OFFSET_SBEULYL)
            ce_symbol = get_symbol(ce_strike, "BUY")
            pe_symbol = get_symbol(pe_strike, "BUY")
            dprint(f"SBEULYL → CE: {ce_symbol}, PE: {pe_symbol}", Fore.YELLOW)

            if not ce_active:
                print(f"{Fore.CYAN}🚀 Placing CE Buy: {ce_symbol}")
                execute_order(client, ce_symbol, LOT_SIZE, "BUY")
            if not pe_active:
                print(f"{Fore.MAGENTA}🚀 Placing PE Buy: {pe_symbol}")
                execute_order(client, pe_symbol, LOT_SIZE, "BUY")
            return

        # --- NORMAL SIGNALS (ATM / OTM) ---
        if sig in ["ATMBUY", "OTMBUY"]:
            side = "BUY"
            offset = OFFSET_ATM if sig.startswith("ATM") else OFFSET_OTM
        elif sig in ["ATMSELL", "OTMSELL"]:
            side = "SELL"
            offset = OFFSET_ATM if sig.startswith("ATM") else OFFSET_OTM
        else:
            print(f"{Fore.YELLOW}💤 Waiting: {entry_signal}")
            return

        strike = round_up_50(ltp + offset) if side == "BUY" else round_down_50(ltp - offset)
        symbol = get_symbol(strike, side)
        dprint(f"Built Symbol: {symbol} for Strike: {strike}")

        if not symbol or symbol == "NA":
            print(f"{Fore.RED}❌ Could not build symbol for strike {strike}")
            return

        # --- Execution ---
        res = {"stat": "Skipped"}
        if side == "BUY" and not ce_active:
            print(f"{Fore.CYAN}🚀 Placing CE Buy: {symbol}")
            res = execute_order(client, symbol, LOT_SIZE, "BUY")
        elif side == "SELL" and not pe_active:
            print(f"{Fore.MAGENTA}🚀 Placing PE Buy: {symbol}")
            res = execute_order(client, symbol, LOT_SIZE, "SELL")
        else:
            dprint(f"Execution skipped. Active? {ce_active if side=='BUY' else pe_active}")

        # --- Dashboard ---
        funds = get_available_funds(client)
        status = f"{Fore.GREEN}Ok" if any(k in str(res) for k in ["nOrderId", "order_id"]) else f"{Fore.RED}Failed/Skipped"
        print(f"""
         =================================
           💰 Cash   : {int(funds)}
           ⚡ Pos    : {pos}
           🎫 Symbol : {symbol}
           📊 Strike : {strike}
           🎯 Action : {entry_signal}
           🔁 Signal : {reversal}
           📌 Status : {status}
         =================================
        """)

    except Exception:
        if DEBUG:
            print(f"{Fore.RED}{traceback.format_exc()}")
        else:
            print(f"{Fore.RED}❌ Main execution error. Enable DEBUG for details.")

if __name__ == "__main__":
    asyncio.run(main())
