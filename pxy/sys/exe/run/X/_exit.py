# _exit.py
import sys
import asyncio
import os
import json
from datetime import datetime, time as dt_time
import pytz
from colorama import Fore, init, Style

# =====================================================================
# GLOBAL STRATEGY RISK PROFILE
# =====================================================================
LOT_SIZE = 65     
MIN_EXIT_PROFIT = 200         # Must yield > ₹200 to trigger side exit
LOOP_INTERVAL_SECONDS = 5     
LEDGER_FILE = "_ledger.json"

init(autoreset=True)

def clear_screen():
    """Cleans terminal view buffer matrix for sharp dashboard updates."""
    os.system('cls' if os.name == 'nt' else 'clear')

def pop_from_json_ledger(index_to_remove):
    """Permanently deletes the matched FIFO node from tracking logs once covered."""
    if os.path.exists(LEDGER_FILE):
        try:
            with open(LEDGER_FILE, "r") as f: ledger = json.load(f)
            removed = ledger.pop(index_to_remove)
            with open(LEDGER_FILE, "w") as f: json.dump(ledger, f, indent=4)
            print(Fore.MAGENTA + f"\n🧹 FIFO PURGE: Removed {removed['symbol']} node from shared ledger.")
        except Exception as e:
            print(f"Ledger file pop error: {e}")

def execute_exit(client, symbol, qty, txn_type, ledger_index):
    try:
        order_tag = f"{datetime.now().strftime('%H%M%S')}_EX"
        params = {
            "exchange_segment": "nse_fo", "product": "NRML", "price": "0",
            "order_type": "MKT", "quantity": str(qty), "validity": "DAY",
            "trading_symbol": symbol, "transaction_type": txn_type, "amo": "NO", "tag": order_tag  
        }
        res = client.place_order(**params)
        if res and str(res).strip():
            print(Fore.MAGENTA + Style.BRIGHT + f"\n🏁 EXIT SUCCESS | SYMBOL: {symbol} | TYPE: {txn_type}")
            pop_from_json_ledger(ledger_index)
            return True
    except Exception as e:
        print(f"Exit routing failure: {e}")
    return False

async def exit_cycle():
    IST = pytz.timezone("Asia/Kolkata")
    now = datetime.now(IST).time()
    if (dt_time(9, 14) <= now < dt_time(9, 16)) or (dt_time(15, 19) <= now < dt_time(15, 31)): 
        clear_screen()
        print(Fore.YELLOW + "⏳ System idling: Market buffer timing block active.")
        return

    # Read tracking transactions log file
    ledger = []
    if os.path.exists(LEDGER_FILE):
        try:
            with open(LEDGER_FILE, "r") as f: ledger = json.load(f)
        except: pass

    from _sgnl import get_all_data
    from _clnt import get_session
    
    data = get_all_data()
    entry_signal = str(data.get("entry", "")).upper().strip()
    ltp = float(data.get("price", 0))
    
    if ltp == 0 or not entry_signal:
        clear_screen()
        print(Fore.RED + "❌ Signal Feed Stream Disconnected or LTP is 0. Attempting retry...")
        return

    client = get_session()
    if not client: return

    # Clear screen frame context to start refreshing the live table matrix
    clear_screen()
    print("━" * 68) 
    print(f" {Fore.YELLOW}{Style.BRIGHT}{'FIFO ACTIVE REAL-TIME MONITOR DASHBOARD':^66}")
    print("━" * 68)
    print(f" LIVE INDEX LTP: {Fore.CYAN}{ltp:<12} {Fore.RESET}| TREND SIGNAL STATE: {Fore.MAGENTA}{entry_signal}")
    print(f" SCAN INTERVAL: {Fore.WHITE}{LOOP_INTERVAL_SECONDS}s {Fore.RESET}        | COMPULSORY EXIT THRESHOLD: {Fore.GREEN}> +₹{MIN_EXIT_PROFIT}")
    print("─" * 68) 
    print(f" {'ID':<3}{'TARGET SYMBOL':<22}{'SIDE':<8}{'ENTRY PRICE':<14}{'LIVE RUNNING PNL':>14}") 
    print("─" * 68) 

    if not ledger:
        print(f" {Fore.WHITE}{Style.DIM}{'No active open tracking positions inside shared JSON profile ledger.':^66}")
        print("━" * 68)
        return

    exit_executed = False

    # --- FIFO PIPELINE PROCESSING & LIVE TABLE DRAW ENGINE ---
    for index, open_trade in enumerate(ledger):
        trade_pnl = 0.0
        
        # A. Calculate Live Matrix for Open Long CE (Bought at .100)
        if open_trade['txn_type'] == "B":
            trade_pnl = (ltp - open_trade['entry_ltp']) * LOT_SIZE
            side_str = f"{Fore.GREEN}LONG"
            
            # Reversal Exit Signal Evaluation: Red Candle confirmation
            if entry_signal in ["SELL", "BEAR"] and trade_pnl > MIN_EXIT_PROFIT and not exit_executed:
                pnl_str = f"TARGET HIT"
                print(f" [{index}] {open_trade['symbol']:<22} {side_str:<8} {open_trade['entry_ltp']:<14} {Fore.GREEN}{pnl_str:>14}")
                if execute_exit(client, open_trade['symbol'], open_trade['qty'], "S", index):
                    exit_executed = True
                    break

        # B. Calculate Live Matrix for Open Short CE (Shorted at .50)
        elif open_trade['txn_type'] == "S":
            trade_pnl = (open_trade['entry_ltp'] - ltp) * LOT_SIZE
            side_str = f"{Fore.RED}SHORT"
            
            # Reversal Exit Signal Evaluation: Green Candle confirmation
            if entry_signal in ["BUY", "BULL"] and trade_pnl > MIN_EXIT_PROFIT and not exit_executed:
                pnl_str = f"TARGET HIT"
                print(f" [{index}] {open_trade['symbol']:<22} {side_str:<8} {open_trade['entry_ltp']:<14} {Fore.GREEN}{pnl_str:>14}")
                if execute_exit(client, open_trade['symbol'], open_trade['qty'], "B", index):
                    exit_executed = True
                    break

        # Continuous live tracking row display
        pnl_color = Fore.GREEN if trade_pnl >= 0 else Fore.RED
        print(f" [{index}] {open_trade['symbol']:<22} {side_str:<8} {open_trade['entry_ltp']:<14.2f} {pnl_color}₹{int(trade_pnl):>13}")

    print("━" * 68)
    print(f" Active Tracking Lots Array Count: {len(ledger)} | Matrix Clock: {datetime.now(IST).strftime('%H:%M:%S')}")

async def main():
    while True:
        try: await exit_cycle()
        except Exception as e: print(f"⚠️ Dashboard View Failure: {e}")
        await asyncio.sleep(LOOP_INTERVAL_SECONDS)

if __name__ == "__main__":
    asyncio.run(main())
