# _exit.py
import asyncio
import os
from datetime import datetime, time as dt_time
import pytz

from colorama import Fore, init, Style
from _sgnl import _pad_line_to_42
from _ltp import get_option_live_ltp  
from _clnt import get_session

LOT_SIZE = 65
MIN_EXIT_PROFIT = 200

init(autoreset=True)

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

# ----------------- 🛑 ORDER EXECUTION disabled FOR DRY RUN -----------------
def execute_exit(client, symbol, qty, txn_type, entry_tag):
    """ Neutralised exit function to ensure safe dry-run monitoring """
    return False 

# ----------------- TRIPLE-STAGE VISUAL MAPPER ENGINE -----------------
def render_comprehensive_order_diagnostics(client):
    """
    Fetches raw information directly from the broker report and breaks 
    the architecture down into explicit processing layers.
    """
    try:
        order_res = client.order_report()  
        orders = order_res.get("data", []) if isinstance(order_res, dict) else order_res
        
        if not isinstance(orders, list):
            print(_pad_line_to_42("❌ BROKER API ERROR: Data is not a list", Fore.RED, Style.RESET_ALL))
            return []

        # =====================================================================
        # STAGE 1: RAW BROKER ORDERS REPORT
        # =====================================================================
        print(_pad_line_to_42("📦 STAGE 1: RAW BROKER ORDER BOOK", Fore.CYAN + Style.BRIGHT, Style.RESET_ALL))
        if not orders:
            print(_pad_line_to_42("  EMPTY BOOK: No orders found today.", Fore.LIGHTBLACK_EX, Style.RESET_ALL))
        for idx, o in enumerate(orders):
            raw_tag = o.get("tag") or o.get("ordModNo") or "NO_TAG"
            raw_sym = o.get("trdSym", "UNKNOWN")
            raw_qty = o.get("fldQty", 0)
            raw_stat = o.get("stat", "UNKNOWN")
            raw_txn = o.get("trnsTp", "?")
            print(_pad_line_to_42(f"  [{idx}] {raw_txn} | {raw_sym} | Qty:{raw_qty} | Stat:{raw_stat} | Tag:{raw_tag}", Fore.LIGHTBLACK_EX, Style.RESET_ALL))
        
        print(_pad_line_to_42("=" * 42, Fore.YELLOW, Style.RESET_ALL))

        # =====================================================================
        # STAGE 2: MAPPED STRUCTURAL ORDERS
        # =====================================================================
        print(_pad_line_to_42("🗺️ STAGE 2: STRATEGIC TAG MAPPING", Fore.MAGENTA + Style.BRIGHT, Style.RESET_ALL))
        
        raw_entries = {}
        closed_tags = set()

        # Step 2A: Identify and group exit links ending with _X
        for o in orders:
            if str(o.get("stat", "")).lower() != "complete":
                continue
            tag = str(o.get("tag") or o.get("ordModNo") or "").strip().upper()
            if tag.endswith("_X"):
                parent_tag = tag[:-2]
                closed_tags.add(parent_tag)
                print(_pad_line_to_42(f"  🔒 EXIT FOUND -> Links to Parent: {parent_tag}", Fore.LIGHTRED_EX, Style.RESET_ALL))

        # Step 2B: Map core strategic entry layers ending with _BUY or _SELL
        for o in orders:
            if str(o.get("stat", "")).lower() != "complete":
                continue
            tag = str(o.get("tag") or o.get("ordModNo") or "").strip().upper()
            
            if not (tag.endswith("_BUY") or tag.endswith("_SELL")):
                continue

            qty = int(float(o.get("fldQty", 0)))
            if qty <= 0:
                continue

            raw_entries[tag] = {
                "symbol": o.get("trdSym", ""),
                "txn_type": str(o.get("trnsTp", "")).upper().strip(),
                "entry_price": float(o.get("avgPrc", 0)),
                "qty": qty,
                "tag": tag,
                "token": o.get("tok")  
            }
            
            # Map status tracking visualization directly to console
            map_status = "⚠️ UNMATCHED" if tag not in closed_tags else "✔️ FULLY CLOSED"
            map_color = Fore.LIGHTGREEN_EX if tag not in closed_tags else Fore.LIGHTBLACK_EX
            print(_pad_line_to_42(f"  {map_status} ENTRY -> {tag} ({o.get('trdSym', '')})", map_color, Style.RESET_ALL))

        print(_pad_line_to_42("=" * 42, Fore.YELLOW, Style.RESET_ALL))

        # =====================================================================
        # STAGE 3: ISOLATED LEDGER FOR FINAL OPEN CHECK
        # =====================================================================
        open_ledger = [details for tag, details in raw_entries.items() if tag not in closed_tags]
        return open_ledger

    except Exception as e:
        print(_pad_line_to_42(f"❌ Diagnostic Failure {str(e)[:20]}", Fore.RED, Style.RESET_ALL))
        return []

# ----------------- CORE CYCLE RUNTIME -----------------
async def exit_cycle():
    client = get_session()
    if not client:
        print(_pad_line_to_42("❌ SERVER SESSION ERROR", Fore.RED, Style.RESET_ALL))
        return

    from _sgnl import get_all_data
    data = get_all_data()
    entry_signal = str(data.get("entry", "")).upper().strip()
    index_ltp = float(data.get("price", 0))

    clear_screen()
    print(_pad_line_to_42("📋 CORE STRATEGY INSPECTION ENGINE", Fore.YELLOW + Style.BRIGHT, Style.RESET_ALL))
    print(_pad_line_to_42("=" * 42, Fore.YELLOW, Style.RESET_ALL))
    print(_pad_line_to_42(f"INDEX LTP : {index_ltp}", Fore.CYAN, Style.RESET_ALL))
    print(_pad_line_to_42(f"SIGNAL    : {entry_signal}", Fore.MAGENTA, Style.RESET_ALL))
    print(_pad_line_to_42("=" * 42, Fore.YELLOW, Style.RESET_ALL))

    # Trigger structural triple-stage diagnostic report
    ledger = render_comprehensive_order_diagnostics(client)

    print(_pad_line_to_42("🔓 STAGE 3: FINAL ISOLATED OPEN ORDERS", Fore.GREEN + Style.BRIGHT, Style.RESET_ALL))
    if not ledger:
        print(_pad_line_to_42("  NO ACTIVE UNMATCHED TRADES", Fore.WHITE, Style.RESET_ALL))
        print(_pad_line_to_42("=" * 42, Fore.YELLOW, Style.RESET_ALL))
        return

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

# ----------------- ENTRY ROUTINE (SINGLE EXECUTION) -----------------
async def main():
    await exit_cycle()

if __name__ == "__main__":
    asyncio.run(main())

