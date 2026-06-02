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

# --- 📁 AUTOMATED SYSTEM DATABASE HANDLERS ---
def load_trades():
    if not os.path.exists(STATE_FILE): return {}
    try:
        with open(STATE_FILE, "r") as f: return json.load(f)
    except: return {}

def save_trades(trades):
    try:
        with open(STATE_FILE, "w") as f: json.dump(trades, f, indent=4)
    except: pass

def sync_database_from_broker_logs(client):
    """
    Downloads raw broker logs, automatically identifies executed trades,
    and dynamically purges rejected/malformed rogue entries from trades.json.
    """
    try:
        order_res = client.order_report()
        orders = order_res.get("data", []) if isinstance(order_res, dict) else order_res
        if not isinstance(orders, list): return

        trades = load_trades()
        completed_exits = set()
        valid_broker_entries = set()

        # Step A: Aggregate all valid completed strategy exit strings
        for o in orders:
            status = str(o.get("stat", "")).strip().lower()
            if status != "complete": continue
            tag = str(o.get("tag", "")).strip().upper()
            if tag.endswith("_ENTRY_EXIT"):
                parent_tag = tag.replace("_EXIT", "")
                completed_exits.add(parent_tag)
            if tag.endswith("_ENTRY"):
                valid_broker_entries.add(tag)

        # Step B: Identify raw broker entry tags and map to ledger rows
        for o in orders:
            status = str(o.get("stat", "")).strip().lower()
            if status != "complete": continue
            tag = str(o.get("tag", "")).strip().upper()
            
            if not tag.endswith("_ENTRY"): continue

            # If an order executed successfully on the exchange but isn't inside our file yet, initialize it
            if tag not in trades:
                trades[tag] = {
                    "entry_tag": tag,
                    "exit_tag": "PENDING",
                    "symbol": str(o.get("trdSym", "")).upper(),
                    "qty": int(float(o.get("fldQty", 0))),
                    "entry_txn": str(o.get("trnsTp", "")).upper(),
                    "entry_price": float(o.get("avgPrc", 0)),
                    "exit_price": 0.0,
                    "token": str(o.get("tok", "")),
                    "status": "OPEN",
                    "opened_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }

        # Step C: Match completed exit loops and update states instantly
        for tag in list(trades.keys()):
            if tag in completed_exits and trades[tag]["status"] == "OPEN":
                trades[tag]["status"] = "COMPLETED"
                trades[tag]["exit_tag"] = f"{tag}_EXIT"
                # Extract actual asset execution value from broker logs
                for o in orders:
                    if str(o.get("tag", "")).upper() == f"{tag}_EXIT":
                        trades[tag]["exit_price"] = float(o.get("avgPrc", 0))
                        break

        # =====================================================================
        # 🔥 CRITICAL SAFETY SHIELD: AUTO-PURGE ROGUE / REJECTED TRADES
        # =====================================================================
        for tag in list(trades.keys()):
            if trades[tag]["status"] == "OPEN":
                # Condition 1: If the trade exists in JSON but NEVER hit the broker's logs as complete
                # Condition 2: Or if it is stuck with a 0.0 entry price and no execution token
                if tag not in valid_broker_entries or (trades[tag]["entry_price"] == 0.0 and not trades[tag]["token"]):
                    print(_pad_line_to_42(f"🗑️ PURGED REJECTED / ROGUE TRADE: {tag}", Fore.RED + Style.BRIGHT, Style.RESET_ALL))
                    del trades[tag] # Wipe it completely out of memory

        save_trades(trades)
    except Exception as e:
        print(_pad_line_to_42(f"⚠️ Sync Error: {str(e)[:22]}", Fore.RED, Style.RESET_ALL))

def execute_exit(client, symbol, qty, txn_type, entry_tag):
    try:
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
        # 1. Synchronize database state from live broker server logs & clean bad entries
        sync_database_from_broker_logs(client)
        
        trades = load_trades()
        
        # 2. Separate database nodes to compile analytics summary metrics
        completed_trades = {k: v for k, v in trades.items() if v["status"] == "COMPLETED"}
        open_trades = {k: v for k, v in trades.items() if v["status"] == "OPEN"}
        
        # Calculate closed total PnL
        booked_pnl = 0.0
        for _, t in completed_trades.items():
            qty = t["qty"]
            e_prc = t["entry_price"]
            x_prc = t["exit_price"]
            if t["entry_txn"] == "B":
                booked_pnl += (x_prc - e_prc) * qty
            else:
                booked_pnl += (e_prc - x_prc) * qty

        # 3. Process and display metrics data dashboard layout inside console
        border = "=========================================="
        print(f"\n{_pad_line_to_42(border, Fore.BLUE, Style.RESET_ALL)}")
        print(_pad_line_to_42("💼 STRATEGY MANAGEMENT LEDGER", Fore.BLUE + Style.BRIGHT, Style.RESET_ALL))
        print(_pad_line_to_42(border, Fore.BLUE, Style.RESET_ALL))
        
        pnl_color = Fore.GREEN if booked_pnl >= 0 else Fore.RED
        print(_pad_line_to_42(f"✅ COMPLETED TRADES : {len(completed_trades)}", Fore.WHITE, Style.RESET_ALL))
        print(_pad_line_to_42(f"💰 BOOKED PnL      : Rs.{booked_pnl:.2f}", pnl_color + Style.BRIGHT, Style.RESET_ALL))
        print(_pad_line_to_42(f"🔓 ACTIVE / OPEN    : {len(open_trades)}", Fore.WHITE, Style.RESET_ALL))
        print(_pad_line_to_42(border, Fore.BLUE, Style.RESET_ALL))

        if not open_trades:
            print(_pad_line_to_42("🏖️ DB STATE CLEAN | NO OPEN TRADES", Fore.GREEN, Style.RESET_ALL))
            print(_pad_line_to_42(border, Fore.BLUE, Style.RESET_ALL))
            return

        print(_pad_line_to_42("👀 MONITORING OPEN CONTRACT LIFECYCLES:", Fore.YELLOW + Style.BRIGHT, Style.RESET_ALL))
        
        # 4. Step through live running trades to calculate open PnL and match exit rules
        for entry_tag, data in open_trades.items():
            symbol = data["symbol"]
            qty = data["qty"]
            entry_txn = data["entry_txn"]
            entry_price = data["entry_price"]
            token = data["token"]

            if entry_price == 0: continue

            # Fetch active option premium valuation ticker rates safely
            live_ltp = float(get_option_live_ltp(client, token, "nse_fo", fallback_price=0.0) if token else 0)
            if live_ltp == 0:
                print(_pad_line_to_42(f"  ⚠️ {entry_tag[:10]} | Price stream offline", Fore.RED, Style.RESET_ALL))
                continue

            # Calculate precise running profit figures
            if entry_txn == "B":
                live_pnl = (live_ltp - entry_price) * qty
                opposite_txn = "S"
            else:
                live_pnl = (entry_price - live_ltp) * qty
                opposite_txn = "B"

            # Print detailed monitoring line item for this contract block
            run_color = Fore.GREEN if live_pnl >= 0 else Fore.RED
            status_text = f"  🔥 {entry_tag} | {symbol[:15]} | PnL: Rs.{live_pnl:.2f}"
            print(_pad_line_to_42(status_text, run_color, Style.RESET_ALL))

            # Profit threshold ceiling safety check
            if live_pnl >= MIN_EXIT_PROFIT:
                print(_pad_line_to_42("🎯 TARGET MET | COUPLING...", Fore.GREEN + Style.BRIGHT, Style.RESET_ALL))
                
                # Pre-lock database state right before network handshakes to block race condition loops
                trades[entry_tag]["status"] = "COMPLETED"
                save_trades(trades)
                
                success = execute_exit(client, symbol, qty, opposite_txn, entry_tag)
                if success:
                    trades[entry_tag]["exit_price"] = live_ltp
                    trades[entry_tag]["exit_tag"] = f"{entry_tag}_EXIT"
                    save_trades(trades)
                else:
                    # Automatic rollback protection layer
                    trades[entry_tag]["status"] = "OPEN"
                    save_trades(trades)
                    
        print(_pad_line_to_42(border, Fore.BLUE, Style.RESET_ALL))

    except Exception as e:
        print(_pad_line_to_42(f"⚠️ Loop Error: {str(e)[:22]}", Fore.RED, Style.RESET_ALL))

async def main():
    client = get_session()
    if client: 
        await process_stateful_exits(client)

if __name__ == "__main__":
    asyncio.run(main())
