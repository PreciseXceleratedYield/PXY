#!/usr/bin/env python3
import sys
import asyncio
from pathlib import Path
from datetime import datetime, time
import pytz
from colorama import Fore, init, Style
import math
import traceback

# --- GLOBAL DEBUG SWITCH ---
DEBUG = False
# ---------------------------

init(autoreset=True)
LOT_SIZE = 65

# --- CONFIGURABLE OFFSETS ---
ATM_OFFSET     = 0      # ATM strike adjustment (negative for ITM)
OTM_OFFSET     = 200    # OTM strike adjustment
SBEULYL_OFFSET = 300    # SBEULYL special offset
# ---------------------------

# --- DYNAMIC PATH FIX ---
HERE = Path(__file__).resolve().parent
RUN_DIR = HERE / "run"
for p in [HERE, RUN_DIR, HERE.parent]:
    if str(p) not in sys.path:
        sys.path.append(str(p))

# --- DEBUG PRINT HELPER ---
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

# --- EXECUTION ---
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
        if DEBUG: dprint(f"Order Execution Exception: {traceback.format_exc()}", Fore.RED)
        return {"stat": "Not_Ok", "errMsg": str(e)}

# --- MAIN ASYNC LOGIC ---
async def main():
    try:
        IST = pytz.timezone("Asia/Kolkata")
        now = datetime.now(IST).time()
        dprint(f"Current IST Time: {now}")

        # Skip windows
        skip_windows = [
            (time(9, 14), time(9, 16)),
            (time(15, 16), time(15, 31))
        ]
        for start, end in skip_windows:
            if start <= now < end:
                dprint(f"Inside {start.strftime('%H:%M')} - {end.strftime('%H:%M')} buffer. Skipping execution.")
                return

        # Session & Market Data
        client = get_session()
        if not client:
            print(f"{Fore.RED}❌ Session failed")
            return

        df = fetch_yf_data()
        if df is None or df.empty:
            print(f"{Fore.RED}❌ No data from YF")
            return

        # Signal & LTP
        entry_signal, reversal = get_entry_signal(df)
        sig = entry_signal.upper().strip()
        ltp = df['Close'].iloc[-1]
        dprint(f"Raw Signal: {entry_signal} | Reversal: {reversal}")

        # Positions with safe fallback
        try:
            pos = get_position_summary(client)
        except Exception:
            pos = {"1CE": 1, "1PE": 1}  # assume maxed out if error

        dprint(f"Current Positions: {pos}")
        ce_active = "1CE" in pos
        pe_active = "1PE" in pos

        # ------------------------
        # SPECIAL CASE: SBEULYL
        # ------------------------
        if sig == "SBEULYL":
            ce_strike = round_up_50(ltp + SBEULYL_OFFSET)
            pe_strike = round_down_50(ltp - SBEULYL_OFFSET)

            ce_symbol = get_symbol(ce_strike, "BUY")
            pe_symbol = get_symbol(pe_strike, "BUY")

            dprint(f"SBEULYL → CE: {ce_symbol}, PE: {pe_symbol}", Fore.YELLOW)

            if not ce_active:
                print(f"{Fore.CYAN}🚀 Placing CE Buy: {ce_symbol}")
                execute_order(client, ce_symbol, LOT_SIZE, "BUY")
            else:
                print(f"{Fore.YELLOW}⏭ CE {ce_symbol} already active, skipping buy")

            if not pe_active:
                print(f"{Fore.MAGENTA}🚀 Placing PE Buy: {pe_symbol}")
                execute_order(client, pe_symbol, LOT_SIZE, "BUY")
            else:
                print(f"{Fore.YELLOW}⏭ PE {pe_symbol} already active, skipping buy")

            return

        # ------------------------
        # NORMAL ATM / OTM SIGNALS
        # ------------------------
        if sig in ["ATMBUY", "OTMBUY"]:
            side = "BUY"
        else:
            print(f"{Fore.YELLOW}💤 Lets Wait as Signal 💤: {entry_signal} 💤")
            return

        offset = OTM_OFFSET if sig.startswith("OTM") else ATM_OFFSET
        ce_strike = round_up_50(ltp + offset)
        pe_strike = round_down_50(ltp - offset)

        ce_symbol = get_symbol(ce_strike, side)
        pe_symbol = get_symbol(pe_strike, side)
        dprint(f"Built Symbols → CE: {ce_symbol}, PE: {pe_symbol} for Strike CE: {ce_strike}, PE: {pe_strike}")

        # Skip if already active
        if ce_active:
            print(f"{Fore.YELLOW}⏭ CE {ce_symbol} already active, skipping buy")
        else:
            print(f"{Fore.CYAN}🚀 Placing CE Buy: {ce_symbol}")
            res = execute_order(client, ce_symbol, LOT_SIZE, "BUY")
            # Dashboard prints only if a new order is placed
            funds = get_available_funds(client)
            is_ok = any(key in str(res) for key in ["nOrderId", "order_id"])
            status = f"{Fore.GREEN}Ok" if is_ok else f"{Fore.RED}Failed/Skipped"
            print(f"""
             =================================
               💰 {Fore.WHITE}Cash   : {int(funds)}
               ⚡ {Fore.WHITE}Pos    : {pos}
               🎫 {Fore.WHITE}Symbol : {ce_symbol}
               📊 {Fore.WHITE}Strike : {ce_strike}
               🎯 {Fore.WHITE}Action : {entry_signal}
               🔁 {Fore.WHITE}Signal : {reversal}
               📌 {Fore.WHITE}Status : {status}
             =================================
            """)

        if pe_active:
            print(f"{Fore.YELLOW}⏭ PE {pe_symbol} already active, skipping buy")
        else:
            print(f"{Fore.MAGENTA}🚀 Placing PE Buy: {pe_symbol}")
            res = execute_order(client, pe_symbol, LOT_SIZE, "BUY")
            funds = get_available_funds(client)
            is_ok = any(key in str(res) for key in ["nOrderId", "order_id"])
            status = f"{Fore.GREEN}Ok" if is_ok else f"{Fore.RED}Failed/Skipped"
            print(f"""
             =================================
               💰 {Fore.WHITE}Cash   : {int(funds)}
               ⚡ {Fore.WHITE}Pos    : {pos}
               🎫 {Fore.WHITE}Symbol : {pe_symbol}
               📊 {Fore.WHITE}Strike : {pe_strike}
               🎯 {Fore.WHITE}Action : {entry_signal}
               🔁 {Fore.WHITE}Signal : {reversal}
               📌 {Fore.WHITE}Status : {status}
             =================================
            """)

    except Exception:
        if DEBUG:
            print(f"{Fore.RED}{traceback.format_exc()}")
        else:
            print(f"{Fore.RED}❌ Main execution error occurred. Enable DEBUG for details.")

if __name__ == "__main__":
    asyncio.run(main())
