import sys
import asyncio
import os
import pytz
import subprocess
from pathlib import Path
from datetime import datetime
from colorama import Fore, init, Style

# --- CONFIG ---
DEBUG = True  

init(autoreset=True)

# --- PATH SETUP ---
HERE = Path(__file__).resolve().parent
PARENT = HERE.parent
RUN_DIR = HERE / "run"
for p in [HERE, RUN_DIR, PARENT]:
    if str(p) not in sys.path:
        sys.path.append(str(p))

from syscnfgpxy import TICKER

# --- LOT SIZE LOGIC ---
t = TICKER.upper().strip()
LOT_SIZE = 30 if t == "^NSEBANK" else 65 if t == "^NSEI" else None

# --- DEBUG PRINT ---
def dprint(msg, color=Fore.CYAN):
    if DEBUG:
        print(f"{Style.BRIGHT}{color}[FORCE DEBUG] {msg}{Style.RESET_ALL}")

# --- SYSTEM IMPORTS ---
try:
    from syspxy import get_all_data
    from runclntpxy import get_session
    from runfundpxy import get_available_funds
    from runsymbpxy import get_symbol
    dprint("SYSTEM IMPORTS SUCCESSFUL", Fore.GREEN)
except Exception as e:
    print(f"{Fore.RED}IMPORT ERROR: {e}")
    sys.exit(1)

def generate_pxy_tag():
    """Generates pure timestamp tag: HHMMSS"""
    ist = pytz.timezone("Asia/Kolkata")
    return datetime.now(ist).strftime('%H%M%S')

def execute_order(client, symbol, qty):
    try:
        order_tag = generate_pxy_tag()
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
            "tag": order_tag
        }
        res = client.place_order(**params)
        print(f"{Fore.GREEN}🚀 FORCED ORDER PLACED | SYMBOL: {symbol} | TAG: {order_tag}")
        return {"stat": "OK", "raw": res}
    except Exception as e:
        print(f"{Fore.RED}❌ EXECUTION ERROR: {e}")
        return {"stat": "FAIL", "err": str(e)}

def run_action(choice):
    """Processes a chosen action option and fires core execution logic."""
    if choice in ["4", ""]:
        print(f"{Fore.YELLOW}❌ Execution exited.")
        return False  # Break loop
        
    elif choice == "3":
        print(f"{Fore.YELLOW}🔄 Triggering Squareoff Script...")
        target_script = HERE / "exesqrpxy.py"
        if target_script.exists():
            subprocess.run([sys.executable, str(target_script)])
        else:
            print(f"{Fore.RED}❌ File not found: {target_script}")
        return True  # Keep loop going

    elif choice == "1":
        sig = "ATMBUY"
        side_label = "CE"
    elif choice == "2":
        sig = "ATMSELL"
        side_label = "PE"
    else:
        print(f"{Fore.RED}Invalid selection. Enter 1 for BUY, 2 for SELL, 3 for SQUAREOFF, or 4 to exit.")
        return True

    # Core Execution Engine for Option 1 & 2
    print(f"{Fore.MAGENTA}⚡ FORCED BYPASS TRIGGERED: Generating immediate {sig} ({side_label}) order...")

    client = get_session()
    if not client:
        print(f"{Fore.RED}Session generation failed.")
        return True

    data = get_all_data()
    ltp = data.get("price")
    ATM_DISTANCE = 100

    symbol = get_symbol(ltp, sig, ATM_DISTANCE)
    res = {"stat": "SKIPPED"}

    if symbol and symbol != "NA":
        res = execute_order(client, symbol, LOT_SIZE)
    else:
        print(f"{Fore.RED}Failed to resolve market symbol for {sig}.")

    try:
        funds = get_available_funds(client)
    except:
        funds = 0

    print(f"""
 =====================================
    ⚡ FORCE TRANSACTION STATUS
 =====================================
    💰 Cash   : {int(funds)}
    🎫 Symbol : {symbol}
    🎯 Action : {sig} ({side_label})
    📌 Status : {res.get('stat')}
 =====================================
 """)
    return True

async def main():
    # --- CHECK FOR DIRECT COMMAND-LINE ARGUMENT ---
    if len(sys.argv) > 1:
        arg_choice = sys.argv[1].strip()
        dprint(f"Direct bypass triggered via CLI argument: option [{arg_choice}]", Fore.YELLOW)
        run_action(arg_choice)
        return  # End execution immediately after processing direct instruction

    # --- FALLBACK TO INTERACTIVE MENU IF NO ARGUMENTS ---
    while True:
        print(f"\n{Fore.YELLOW}⚡ === EXECUTOR FORCED ENGINE ===")
        print(f"{Fore.WHITE} [1] FORCE BUY (CE)")
        print(f"{Fore.WHITE} [2] FORCE SELL (PE)")
        print(f"{Fore.WHITE} [3] SQUAREOFF")
        print(f"{Fore.WHITE} [4] EXIT")
        
        try:
            choice = input(f"{Fore.CYAN}Select action (1, 2, 3, or 4): {Style.RESET_ALL}").strip()
            should_continue = run_action(choice)
            if not should_continue:
                break
        except (KeyboardInterrupt, SystemExit):
            print(f"\n{Fore.YELLOW}❌ Execution aborted.")
            break

if __name__ == "__main__":
    asyncio.run(main())
