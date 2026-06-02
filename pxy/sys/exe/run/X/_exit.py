# _exit.py
import asyncio
import os
import json
import pytz
from datetime import datetime
from colorama import Fore, init, Style
from _sgnl import _pad_line_to_42
from _ltp import get_option_live_ltp  
from _clnt import get_session

# =====================================================================
# 🎛️ CONFIGURATION SETTINGS & STATE CONTROL
# =====================================================================
MIN_EXIT_PROFIT = 500         
STATE_FILE = "trades.json"

init(autoreset=True)

# --- 📁 EMBEDDED LOCAL STATE MANAGEMENT SYSTEM ---
def load_trades():
    if not os.path.exists(STATE_FILE): return {}
    try:
        with open(STATE_FILE, "r") as f: return json.load(f)
    except: return {}

def save_trades(trades):
    try:
        with open(STATE_FILE, "w") as f: json.dump(trades, f, indent=4)
    except: pass

def record_entry(entry_tag, symbol, qty, txn_type, entry_price, token):
    trades = load_trades()
    trades[entry_tag] = {
        "entry_tag": entry_tag, "exit_tag": "PENDING", "symbol": symbol,
        "qty": int(qty), "entry_txn": txn_type, "entry_price": float(entry_price),
        "exit_price": 0.0, "token": token, "status": "OPEN",
        "opened_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    save_trades(trades)

def record_exit(entry_tag, exit_tag, exit_price):
    trades = load_trades()
    if entry_tag in trades:
        trades[entry_tag]["exit_tag"] = exit_tag
        trades[entry_tag]["exit_price"] = float(exit_price)
        trades[entry_tag]["status"] = "COMPLETED"
        save_trades(trades)

# --- ⚔️ SAFE LIQUIDATION MODULE ---
def execute_exit(client, symbol, qty, txn_type, entry_tag):
    try:
        # Appends matching exit suffix to MMDDHHMMSS_ENTRY key
        exit_tag = f"{entry_tag}_EXIT"
        
        params = {
            "exchange_segment": "nse_fo", "product": "NRML", "price": "0",
            "order_type": "MKT", "quantity": str(qty), "validity": "DAY",
            "trading_symbol": symbol, "transaction_type": txn_type, "amo": "NO", "tag": exit_tag
        }
        res = client.place_order(**params)
        if res and str(res).strip():
            print(_pad_line_to_42(f"🏁 COUPLED | {exit_tag}", Fore.MAGENTA + Style.BRIGHT, Style.RESET_ALL))
            return True
    except Exception as e:
        print(_pad_line_to_42(f"❌ Exit Error {str(e)[:20]}", Fore.RED, Style.RESET_ALL))
    return False

async def process_stateful_exits(client):
    try:
        trades = load_trades()
        
        # PROTECTION GUARD: Isolate only active open logs
        open_trades = {k: v for k, v in trades.items() if v["status"] == "OPEN"}
        
        if not open_trades:
            print(_pad_line_to_42("🏖️ DB STATE CLEAN | NO OPEN TRADES", Fore.GREEN, Style.RESET_ALL))
            return

        for entry_tag, data in open_trades.items():
            symbol = data["symbol"]
            qty = data["qty"]
            entry_txn = data["entry_txn"]
            entry_price = data["entry_price"]
            token = data["token"]

            # Price recovery module from broker logs if needed
            if entry_price == 0:
                try:
                    order_res = client.order_report()
                    orders = order_res.get("data", []) if isinstance(order_res, dict) else order_res
                    for o in orders:
                        if str(o.get("tag", "")).upper() == entry_tag.upper():
                            entry_price = float(o.get("avgPrc", 0))
                            break
                except: pass

            live_ltp = float(get_option_live_ltp(token) if token else 0)
            if live_ltp == 0: continue

            # Dynamic PnL tracking math based strictly on Entry types
            if entry_txn == "B":
                live_pnl = (live_ltp - entry_price) * qty
                opposite_txn = "S"  # Long exits can ONLY sell
            else:
                live_pnl = (entry_price - live_ltp) * qty
                opposite_txn = "B"  # Short exits can ONLY buy back

            print(_pad_line_to_42(f"📊 {entry_tag} | PnL: Rs.{live_pnl:.2f}", Fore.CYAN, Style.RESET_ALL))

            # Profit threshold check
            if live_pnl >= MIN_EXIT_PROFIT:
                print(_pad_line_to_42("🎯 TARGET MET | COUPLING...", Fore.GREEN + Style.BRIGHT, Style.RESET_ALL))
                success = execute_exit(client, symbol, qty, opposite_txn, entry_tag)
                if success:
                    record_exit(entry_tag, f"{entry_tag}_EXIT", live_ltp)

    except Exception as e:
        print(_pad_line_to_42(f"⚠️ Loop Error: {str(e)[:22]}", Fore.RED, Style.RESET_ALL))

async def main():
    client = get_session()
    if client: 
        await process_stateful_exits(client)

if __name__ == "__main__":
    asyncio.run(main())

