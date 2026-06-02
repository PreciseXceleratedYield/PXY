# _exit.py
import asyncio
import os
from datetime import datetime, time as dt_time
import pytz

from colorama import Fore, init, Style
from _sgnl import _pad_line_to_42
from _ltp import get_option_live_ltp  # Uses your 5-tier fallback script
from _clnt import get_session

LOT_SIZE = 65
MIN_EXIT_PROFIT = 200

init(autoreset=True)


# ---------------- SCREEN ----------------
def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')


# ----------------🛑 ORDER EXECUTION DEACTIVATED ----------------
def execute_exit(client, symbol, qty, txn_type, entry_tag):
    """ Simulated order execution wrapper for risk-free system testing. """
    print(_pad_line_to_42(f"⚡ SIMULATED EXIT | {entry_tag} -> {txn_type}", Fore.YELLOW + Style.BRIGHT, Style.RESET_ALL))
    return False 


# ---------------- DIAGNOSTIC TAG MATRIX LEDGER ----------------
def reconstruct_fifo_ledger_from_orders(client):
    """
    Builds an independent position ledger grouped strictly by unique Entry Tags.
    Uses symbol volume netting to pair strategy entries with system-assigned tags.
    """
    try:
        order_res = client.order_report()  
        orders = order_res.get("data", []) if isinstance(order_res, dict) else order_res
        if not isinstance(orders, list):
            print(_pad_line_to_42("❌ BROKER API ERROR: Order report data is not a list", Fore.RED, Style.RESET_ALL))
            return []

        # =====================================================================
        # STAGE 1: SYMBOL QUANTITY VOLUME NETTING (Catches Alphanumeric Exits)
        # =====================================================================
        symbol_net_qty = {}
        for o in orders:
            status = str(o.get("stat", "")).strip().lower()
            if status != "complete": 
                continue
                
            sym = str(o.get("trdSym", "")).strip().upper()
            txn = str(o.get("trnsTp", "")).strip().upper()
            qty = int(float(o.get("fldQty", 0)))
            
            if qty <= 0 or not sym: 
                continue
                
            if sym not in symbol_net_qty:
                symbol_net_qty[sym] = 0
                
            if txn == "B":
                symbol_net_qty[sym] += qty
            elif txn == "S":
                symbol_net_qty[sym] -= qty

        # =====================================================================
        # STAGE 2: PARSING AND CLASSIFYING STRATEGY TAGS
        # =====================================================================
        print("\n" + _pad_line_to_42("🗺️ STAGE 2: STRATEGIC TAG MAPPING", Fore.MAGENTA + Style.BRIGHT, Style.RESET_ALL))
        
        raw_entries = {}
        closed_tags = set()

        # Step 2A: Find entry tags closed out directly via standard automated '_X' suffixes
        for o in orders:
            status = str(o.get("stat", "")).strip().lower()
            if status != "complete": 
                continue
            tag = str(o.get("tag") or o.get("ordModNo") or "").strip().upper()
            if tag.endswith("_X"):
                parent_tag = tag[:-2]
                closed_tags.add(parent_tag)
                print(_pad_line_to_42(f"  🔒 EXPLICIT LINK -> Exit {tag} closes {parent_tag}", Fore.LIGHTRED_EX, Style.RESET_ALL))

        # Step 2B: Compile active strategy entry nodes
        for o in orders:
            status = str(o.get("stat", "")).strip().lower()
            if status != "complete": 
                continue
            tag = str(o.get("tag") or o.get("ordModNo") or "").strip().upper()
            sym = str(o.get("trdSym", "")).strip().upper()
            
            if not (tag.endswith("_B") or tag.endswith("_S")): 
                continue

            qty = int(float(o.get("fldQty", 0)))
            if qty <= 0: 
                continue

            # Check if volume netting closed it before tagging
            is_netted = symbol_net_qty.get(sym, 0) == 0
            is_tagged_closed = tag in closed_tags

            if is_netted or is_tagged_closed:
                map_status = "✔️ FULLY CLOSED (Net Zero)" if is_netted else "✔️ FULLY CLOSED (Tag Match)"
                print(_pad_line_to_42(f"  {map_status} -> {tag} [{sym}]", Fore.LIGHTBLACK_EX, Style.RESET_ALL))
                continue

            print(_pad_line_to_42(f"  ⚠️ UNMATCHED ACTIVE POSITION -> {tag} [{sym}]", Fore.LIGHTGREEN_EX, Style.RESET_ALL))
            raw_entries[tag] = {
                "symbol": sym,
                "txn_type": str(o.get("trnsTp", "")).upper().strip(),
                "entry_price": float(o.get("avgPrc", 0)),
                "qty": qty,
                "tag": tag,
                "token": o.get("tok")  
            }

        print(_pad_line_to_42("=" * 42, Fore.YELLOW, Style.RESET_ALL))
        return list(raw_entries.values())

    except Exception as e:
        print(_pad_line_to_42(f"❌ Ledger Error {str(e)[:20]}", Fore.RED, Style.RESET_ALL))
        return []


# ---------------- MAIN RUNTIME ENGINE PASS ----------------
async def exit_cycle():
    client = get_session()
    if not client:
        return

    from _sgnl import get_all_data

    data = get_all_data()
    entry_signal = str(data.get("entry", "")).upper().strip()
    index_ltp = float(data.get("price", 0))

    clear_screen()
    print(_pad_line_to_42("📋 TAG EXCLUSION STRATEGY ENGINE", Fore.YELLOW + Style.BRIGHT, Style.RESET_ALL))
    print(_pad_line_to_42("=" * 42, Fore.YELLOW, Style.RESET_ALL))
    print(_pad_line_to_42(f"INDEX LTP : {index_ltp}", Fore.CYAN, Style.RESET_ALL))
    print(_pad_line_to_42(f"SIGNAL    : {entry_signal}", Fore.MAGENTA, Style.RESET_ALL))
    print(_pad_line_to_42("=" * 42, Fore.YELLOW, Style.RESET_ALL))

    # Pull unmatched strategy open ledger
    ledger = reconstruct_fifo_ledger_from_orders(client)

    print(_pad_line_to_42("🔓 STAGE 3: ISOLATED LIVE POSITIONS", Fore.GREEN + Style.BRIGHT, Style.RESET_ALL))
    if not ledger:
        print(_pad_line_to_42("  NO UNMATCHED STRATEGY POSITIONS", Fore.WHITE, Style.RESET_ALL))
        print(_pad_line_to_42("=" * 42, Fore.YELLOW, Style.RESET_ALL))
        return

    # Process and display live unmatched active trades metrics
    for i, t in enumerate(ledger):
        option_ltp = get_option_live_ltp(
            client=client,
            token_id=t["token"],
            ex_seg="nse_fo",
            fallback_price=t["entry_price"]
        )

        pnl = 0.0 
        
        if t["txn_type"] == "B":
            pnl = (option_ltp - t["entry_price"]) * t["qty"]
            if pnl >= MIN_EXIT_PROFIT and entry_signal in ["SELL", "BEAR"]:
                print(_pad_line_to_42(f"  [⚡] MATCH MET -> {t['tag']}", Fore.YELLOW, Style.RESET_ALL))

        elif t["txn_type"] == "S":
            pnl = (t["entry_price"] - option_ltp) * t["qty"]
            if pnl >= MIN_EXIT_PROFIT and entry_signal in ["BUY", "BULL"]:
                print(_pad_line_to_42(f"  [⚡] MATCH MET -> {t['tag']}", Fore.YELLOW, Style.RESET_ALL))

        color = Fore.GREEN if pnl >= 0 else Fore.RED
        print(_pad_line_to_42(
            f"  🔥 [{i}] {t['tag']} PnL:{int(pnl)} (LTP:{option_ltp:.2f})",
            color,
            Style.RESET_ALL
        ))
    print(_pad_line_to_42("=" * 42, Fore.YELLOW, Style.RESET_ALL))


# ---------------- ENTRY ROUTINE (SINGLE EXECUTION) ----------------
async def main():
    try:
        await exit_cycle()
    except Exception as e:
        print(_pad_line_to_42(f"❌ Diagnostic Failure: {str(e)[:22]}", Fore.RED, Style.RESET_ALL))

if __name__ == "__main__":
    asyncio.run(main())

