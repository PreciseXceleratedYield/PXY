#!/usr/bin/env python3
import sys
import asyncio
from pathlib import Path
from datetime import datetime, time
import pytz
from colorama import Fore, init, Style
import math
import traceback

# --- FULL DEBUG SWITCH ---
DEBUG = True  # Enable full debug
init(autoreset=True)
LOT_SIZE = 65  # Maximum qty per symbol

# --- CONFIGURABLE OFFSETS ---
IST = pytz.timezone("Asia/Kolkata")
today = datetime.now(IST).weekday()  # Monday=0 ... Friday=4
ATM_OFFSET = [0, -50, -100, -150, -200][today] if today <= 4 else 0
OTM_OFFSET = ATM_OFFSET + 200
SBEULYL_OFFSET = ATM_OFFSET + 300

print(f"Today:{today}|ATM:{ATM_OFFSET}|OTM:{OTM_OFFSET}|SBEULYL:{SBEULYL_OFFSET}")

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

# --- DASHBOARD PRINT HELPER ---
def print_dashboard(funds, pos, symbol, strike, action, signal, status, qty_bought):
    print(f"""
     =================================
       💰 {Fore.WHITE}Cash   : {int(funds)}
       ⚡ {Fore.WHITE}Pos    : {pos.get(symbol, 0)}
       🎫 {Fore.WHITE}Symbol : {symbol}
       📊 {Fore.WHITE}Strike : {strike}
       🎯 {Fore.WHITE}Action : {action}
       🔁 {Fore.WHITE}Signal : {signal}
       📌 {Fore.WHITE}Status : {status} | Bought Qty: {qty_bought}
     =================================
    """)

# --- EXECUTION WITH FIXED TRANSACTION TYPE ---
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
            "transaction_type": "B" if side.upper() == "BUY" else "S",
            "amo": "NO",
            "disclosed_quantity": "0",
            "market_protection": "0"
        }
        dprint(f"Executing Order for {symbol} | Params: {params}", Fore.YELLOW)
        res = client.place_order(**params)
        dprint(f"[API RESPONSE] {res}", Fore.MAGENTA)
        return res if res else {"stat": "Not_Ok", "errMsg": "No response from API"}
    except Exception as e:
        dprint(f"Order Execution Exception: {traceback.format_exc()}", Fore.RED)
        return {"stat": "Not_Ok", "errMsg": str(e)}

# --- STRICT SAFE BUY WITH FULL DEBUG ---
orders_placed = set()  # Track symbols ordered this run

def safe_buy(client, symbol, max_qty=LOT_SIZE):
    try:
        pos = {}
        try:
            pos = get_position_summary(client)
            dprint(f"Position Summary: {pos}", Fore.BLUE)
            if not isinstance(pos, dict):
                pos = {}
        except Exception as e:
            dprint(f"Position fetch exception: {e}", Fore.RED)
            pos = {}

        current_qty = pos.get(symbol, 0)
        dprint(f"Current qty for {symbol}: {current_qty}", Fore.CYAN)

        if current_qty >= max_qty:
            print(f"{Fore.YELLOW}⏭ {symbol} already at max {current_qty}, skipping buy")
            return 0
        if symbol in orders_placed:
            print(f"{Fore.YELLOW}⏭ Already bought {symbol} in this run, skipping")
            return 0

        buy_qty = max_qty - current_qty
        if buy_qty <= 0:
            print(f"{Fore.YELLOW}⏭ Nothing to buy for {symbol}, skipping")
            return 0

        print(f"{Fore.CYAN}🚀 SAFE BUY: {symbol} | Qty: {buy_qty} | Current: {current_qty}")
        res = execute_order(client, symbol, buy_qty, "BUY")
        dprint(f"Order execution result: {res}", Fore.MAGENTA)
        orders_placed.add(symbol)
        return buy_qty
    except Exception as e:
        print(f"{Fore.RED}❌ Error in safe_buy for {symbol}: {e}")
        return 0

# --- MAIN ASYNC LOGIC WITH FULL DEBUG ---
async def main():
    try:
        now = datetime.now(IST).time()
        dprint(f"Current IST Time: {now}")

        # Skip buffer windows
        skip_windows = [
            (time(9, 14), time(9, 16)),
            (time(15, 16), time(15, 31))
        ]
        for start, end in skip_windows:
            if start <= now < end:
                dprint(f"Inside {start.strftime('%H:%M')} - {end.strftime('%H:%M')} buffer. Skipping execution.")
                return

        client = get_session()
        if not client:
            print(f"{Fore.RED}❌ Session failed")
            return

        df = fetch_yf_data()
        if df is None or df.empty:
            print(f"{Fore.RED}❌ No data from YF")
            return

        entry_signal, reversal = get_entry_signal(df)
        sig = entry_signal.upper().strip()
        ltp = df['Close'].iloc[-1]
        dprint(f"Raw Signal: {entry_signal} | Reversal: {reversal}", Fore.GREEN)
        dprint(f"LTP: {ltp}", Fore.GREEN)

        funds = get_available_funds(client)
        try:
            pos = get_position_summary(client)
            dprint(f"Fetched Position Summary: {pos}", Fore.BLUE)
            if not isinstance(pos, dict):
                pos = {}
        except Exception:
            pos = {}

        # SBEULYL: buy both CE & PE
        if sig == "SBEULYL":
            ce_strike = round_up_50(ltp + SBEULYL_OFFSET)
            pe_strike = round_down_50(ltp - SBEULYL_OFFSET)
            ce_symbol = get_symbol(ce_strike, "BUY")
            pe_symbol = get_symbol(pe_strike, "BUY")
            qty_ce = safe_buy(client, ce_symbol)
            qty_pe = safe_buy(client, pe_symbol)
            print_dashboard(funds, pos, ce_symbol, ce_strike, "BUY", sig, Fore.GREEN + "Ok", qty_ce)
            print_dashboard(funds, pos, pe_symbol, pe_strike, "BUY", sig, Fore.GREEN + "Ok", qty_pe)

        # ATMBUY / OTMBUY → buy CE
        elif sig in ["ATMBUY", "OTMBUY"]:
            offset = OTM_OFFSET if sig.startswith("OTM") else ATM_OFFSET
            ce_strike = round_up_50(ltp + offset)
            ce_symbol = get_symbol(ce_strike, "BUY")
            qty_ce = safe_buy(client, ce_symbol)
            print_dashboard(funds, pos, ce_symbol, ce_strike, "BUY", sig, Fore.GREEN + "Ok", qty_ce)

        # ATMSELL / OTMSSELL → buy PE
        elif sig in ["ATMSELL", "OTMSELL"]:
            offset = OTM_OFFSET if sig.startswith("OTM") else ATM_OFFSET
            pe_strike = round_down_50(ltp - offset)
            pe_symbol = get_symbol(pe_strike, "BUY")
            qty_pe = safe_buy(client, pe_symbol)
            print_dashboard(funds, pos, pe_symbol, pe_strike, "BUY", sig, Fore.GREEN + "Ok", qty_pe)

        else:
            print(f"{Fore.YELLOW}💤 Waiting as Signal: {entry_signal} 💤")
            return

    except Exception:
        print(f"{Fore.RED}{traceback.format_exc()}")

if __name__ == "__main__":
    asyncio.run(main())
