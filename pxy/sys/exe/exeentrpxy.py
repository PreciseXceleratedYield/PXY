import sys
import asyncio
from pathlib import Path
from datetime import datetime, time
import pytz
from colorama import Fore, init, Style
import math
import traceback

# --- GLOBAL DEBUG SWITCH ---
DEBUG = True  # Set to False for production / "no"
# ---------------------------

init(autoreset=True)
LOT_SIZE = 65

# --- DYNAMIC PATH FIX ---
HERE = Path(__file__).resolve().parent
RUN_DIR = HERE / "run"

if str(HERE) not in sys.path: sys.path.append(str(HERE))
if str(RUN_DIR) not in sys.path: sys.path.append(str(RUN_DIR))
if str(HERE.parent) not in sys.path: sys.path.append(str(HERE.parent))

# --- DEBUG PRINT HELPER ---
def dprint(msg, color=Fore.CYAN):
    """Prints debug messages only if DEBUG is enabled."""
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

# --- EXECUTION (DEBUGGED) ---
def execute_order(client, symbol, qty, side):
    """Executes Market Buy with parameter logging."""
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

        # Buffer check
        # Define all skip windows
        skip_windows = [
            (time(9, 14), time(9, 16)),    # 9:14 AM - 9:16 AM
            (time(15, 16), time(15, 31))   # 3:16 PM - 3:31 PM
        ]
        
        # Check if current time is inside any skip window
        for start, end in skip_windows:
            if start <= now < end:
                dprint(f"Inside {start.strftime('%H:%M')} - {end.strftime('%H:%M')} buffer. Skipping execution.")
                return

        # 1. Session Initialization
        dprint("Authenticating session...")
        client = get_session()
        if not client:
            print(f"{Fore.RED}❌ Session failed")
            return

        # 2. Market Data Retrieval
        dprint("Fetching Yahoo Finance data...")
        df = fetch_yf_data()
        if df is None or df.empty:
            print(f"{Fore.RED}❌ No data from YF")
            return

        # 3. Signal & Position Analysis
        entry_signal, reversal = get_entry_signal(df)
        dprint(f"Raw Signal: {entry_signal} | Reversal: {reversal}")
        
        pos = get_position_summary(client)
        dprint(f"Current Positions: {pos}")
        
        ce_active = "1CE" in pos
        pe_active = "1PE" in pos

        ltp = df['Close'].iloc[-1]
        dprint(f"Current LTP: {ltp}")

        # --- 4. Side & Strike Logic (ADJUSTED FOR ATM/OTM ONLY) ---
        sig = entry_signal.upper().strip()

        # Determine side strictly from ATM/OTM signal
        if sig in ["ATMBUY", "OTMBUY"]:
            side = "BUY"
        elif sig in ["ATMSELL", "OTMSELL"]:
            side = "SELL"
        else:
            print(f"{Fore.YELLOW}💤 Lets Wait as Signal 💤: 💤   {entry_signal}  💤")
            return

        # Determine offset: ATM → 0, OTM → 200
        offset = 200 if sig.startswith("OTM") else 0

        # Strike calculation
        if side == "BUY":
            strike = round_up_50(ltp + offset)
        else:
            strike = round_down_50(ltp - offset)

        # 5. Symbol Building
        symbol = get_symbol(strike, side)
        dprint(f"Built Symbol: {symbol} for Strike: {strike}")

        if not symbol or symbol == "NA":
            print(f"{Fore.RED}❌ Could not build symbol for strike {strike}")
            return

        # 6. Execution Block
        res = {"stat": "Skipped"}
        if side == "BUY" and not ce_active:
            print(f"{Fore.CYAN}🚀 Placing CE Buy: {symbol}")
            res = execute_order(client, symbol, LOT_SIZE, "BUY")
        elif side == "SELL" and not pe_active:
            print(f"{Fore.MAGENTA}🚀 Placing PE Buy: {symbol}")
            res = execute_order(client, symbol, LOT_SIZE, "SELL")
        else:
            dprint(f"Execution skipped. Condition: {side} Active? {ce_active if side == 'BUY' else pe_active}")

        # 7. Final Dashboard
        funds = get_available_funds(client)
        is_ok = any(key in str(res) for key in ["nOrderId", "order_id"])
        status = f"{Fore.GREEN}Ok" if is_ok else f"{Fore.RED}Failed/Skipped"

        print(f"""
         =================================
           💰 {Fore.WHITE}Cash   : {int(funds)}
           ⚡ {Fore.WHITE}Pos    : {pos}
           🎫 {Fore.WHITE}Symbol : {symbol}
           📊 {Fore.WHITE}Strike : {strike}
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
