import asyncio
import os
import json
import pytz
from datetime import datetime
from colorama import Fore, init, Style
from _sgnl import _pad_line_to_42
from _ltp import get_option_live_ltp  
from _clnt import get_session
import subprocess


# =====================================================================
# 🎛️ CONFIGURATION SETTINGS & STATE CONTROL
# =====================================================================
MIN_EXIT_PROFIT = 300         
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
            
            # Slicing exactly the last 5 characters ("_EXIT") to isolate closed loops
            if tag.endswith("_ENTRY_EXIT"):
                parent_tag = tag[:-5] 
                completed_exits.add(parent_tag)
            if tag.endswith("_ENTRY"):
                valid_broker_entries.add(tag)

        # Step B: Identify raw broker entry tags and map to ledger rows
        for o in orders:
            status = str(o.get("stat", "")).strip().lower()
            if status != "complete": continue
            tag = str(o.get("tag", "")).strip().upper()
            
            if not tag.endswith("_ENTRY"): continue

            # Initialize ONLY if it hit exchange as complete _ENTRY and isn't tracked yet
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
                    "current_signal": "NONE",
                    "opened_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }

        # Step C: Match completed exit loops and update states instantly
        for tag in list(trades.keys()):
            if tag in completed_exits and trades[tag]["status"] == "OPEN":
                trades[tag]["status"] = "COMPLETED"
                trades[tag]["exit_tag"] = f"{tag}_EXIT"
                for o in orders:
                    if str(o.get("tag", "")).upper() == f"{tag}_EXIT":
                        trades[tag]["exit_price"] = float(o.get("avgPrc", 0))
                        break

        # =====================================================================
        # 🔥 CRITICAL SAFETY SHIELD: AUTO-PURGE ROGUE / REJECTED TRADES
        # =====================================================================
        for tag in list(trades.keys()):
            if trades[tag]["status"] == "OPEN":
                if tag not in valid_broker_entries or (trades[tag]["entry_price"] == 0.0 and not trades[tag]["token"]):
                    print(_pad_line_to_42(f"🗑️ PURGED REJECTED / ROGUE TRADE: {tag}", Fore.RED + Style.BRIGHT, Style.RESET_ALL))
                    del trades[tag]

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
            print(_pad_line_to_42(f"🏁 CLOSED POSITION | {exit_tag}", Fore.MAGENTA + Style.BRIGHT, Style.RESET_ALL))
            try:
                subprocess.Popen(["python", "_pnl.py"])
            except Exception as e:
                print(_pad_line_to_42(f"⚠️ Script Trigger Error: {str(e)[:20]}", Fore.RED, Style.RESET_ALL))
            return True
    except Exception as e:
        print(_pad_line_to_42(f"❌ Exit Error {str(e)[:20]}", Fore.RED, Style.RESET_ALL))
    return False

async def process_stateful_exits(client):
    try:
        sync_database_from_broker_logs(client)
        trades = load_trades()
        
        completed_trades = {k: v for k, v in trades.items() if v["status"] == "COMPLETED"}
        
        # Filter strictly for open candidates (_ENTRY is present, but NO _ENTRY_EXIT has fired yet)
        exit_candidates = {k: v for k, v in trades.items() if v["status"] == "OPEN"}
        
        booked_pnl = 0.0
        for _, t in completed_trades.items():
            qty = t["qty"]
            e_prc = t["entry_price"]
            x_prc = t["exit_price"]
            if t["entry_txn"] == "B":
                booked_pnl += (x_prc - e_prc) * qty
            else:
                booked_pnl += (e_prc - x_prc) * qty

        border = "=========================================="
        print(f"\n{_pad_line_to_42(border, Fore.BLUE, Style.RESET_ALL)}")
        print(_pad_line_to_42("   PXY® PreciseXceleratedYield Pvt Ltd™", Fore.BLUE + Style.BRIGHT, Style.RESET_ALL))
        print(_pad_line_to_42(border, Fore.BLUE, Style.RESET_ALL))
        
        pnl_color = Fore.GREEN if booked_pnl >= 0 else Fore.RED
        print(_pad_line_to_42(f"✅ COMPLETED TRADES : {len(completed_trades)}", Fore.WHITE, Style.RESET_ALL))
        print(_pad_line_to_42(f"💰 BOOKED PnL       : Rs.{booked_pnl:.2f}", pnl_color + Style.BRIGHT, Style.RESET_ALL))
        print(_pad_line_to_42(f"🔓 EXIT CANDIDATES  : {len(exit_candidates)}", Fore.WHITE, Style.RESET_ALL))
        print(_pad_line_to_42(border, Fore.BLUE, Style.RESET_ALL))

        if not exit_candidates:
            print(_pad_line_to_42("🏖️ DB STATE CLEAN | NO OPEN CANDIDATES", Fore.GREEN, Style.RESET_ALL))
            print(_pad_line_to_42(border, Fore.BLUE, Style.RESET_ALL))
            return

        print(_pad_line_to_42("👀 EXIT CANDIDATES ON WAIT:", Fore.YELLOW + Style.BRIGHT, Style.RESET_ALL))
        
        for entry_tag, data in exit_candidates.items():
            symbol = data["symbol"]
            qty = data["qty"]
            entry_txn = data["entry_txn"]
            entry_price = data["entry_price"]
            token = data["token"]

            if entry_price == 0: continue

            live_ltp = float(get_option_live_ltp(client, token, "nse_fo", fallback_prc=entry_price))
            
            if entry_txn == "B":
                unrealized_pnl = (live_ltp - entry_price) * qty
                exit_txn_type = "S"
            else:
                unrealized_pnl = (entry_price - live_ltp) * qty
                exit_txn_type = "B"

            current_signal = str(data.get("current_signal", "NONE")).strip().upper()

            is_opposite_signal = False
            if entry_txn == "B" and current_signal == "SELL":
                is_opposite_signal = True
            elif entry_txn == "S" and current_signal == "BUY":
                is_opposite_signal = True

            pnl_str_color = Fore.GREEN if unrealized_pnl >= 0 else Fore.RED
            metrics_display = f"{symbol[:10]} | PnL: Rs.{unrealized_pnl:.1f} | Sig: {current_signal}"
            print(_pad_line_to_42(metrics_display, pnl_str_color, Style.RESET_ALL))

            # --- DUAL-CONDITION AND LOGIC GATE ---
            if unrealized_pnl >= MIN_EXIT_PROFIT and is_opposite_signal:
                print(_pad_line_to_42(f"🎯 MATCHED: PROFIT & OPPOSITE SIGNAL!", Fore.GREEN + Style.BRIGHT, Style.RESET_ALL))
                success = execute_exit(client, symbol, qty, exit_txn_type, entry_tag)
                if success:
                    sync_database_from_broker_logs(client)
            else:
                if unrealized_pnl < MIN_EXIT_PROFIT and not is_opposite_signal:
                    status_reason = "Waiting for profit & signal"
                elif unrealized_pnl < MIN_EXIT_PROFIT:
                    status_reason = "Profit too low"
                else:
                    status_reason = "Waiting for opposite signal"
                print(_pad_line_to_42(f"⏳ HOLDING: {status_reason}", Fore.YELLOW, Style.RESET_ALL))
                    
        print(_pad_line_to_42(border, Fore.BLUE, Style.RESET_ALL))

    except Exception as e:
        print(_pad_line_to_42(f"⚠️ System Error: {str(e)[:30]}", Fore.RED, Style.RESET_ALL))

# --- SINGLE-RUN EXECUTION HARNESS ---
async def main():
    client = get_session()
    if not client:
        print("❌ Session failed. Exiting script.")
        return
        
    await process_stateful_exits(client)

if __name__ == "__main__":
    asyncio.run(main())
