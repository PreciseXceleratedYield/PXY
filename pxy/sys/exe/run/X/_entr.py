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

# ----------------- 🛑 ORDER EXECUTION DISABLED -----------------
def execute_exit(client, symbol, qty, txn_type, entry_tag):
    """ Simulated order placement for safe monitoring. """
    exit_tag = f"{entry_tag}_X"
    print(_pad_line_to_42(f"⚠️ SIMULATED EXIT | {entry_tag}", Fore.YELLOW, Style.RESET_ALL))
    return False # Returns False to prevent writing to closed trade log files

# ----------------- MASTER ORDER LEDGER RECONSTRUCTION -----------------
def analyze_and_map_all_orders(client):
    """
    Scans the complete order report, separates entries from exits, 
    and returns explicit structural lists of both open and closed states.
    """
    try:
        order_res = client.order_report()  
        orders = order_res.get("data", []) if isinstance(order_res, dict) else order_res
        if not isinstance(orders, list):
            return [], []

        raw_entries = {}
        closed_tags = set()

        # PASS 1: Log all successfully executed exit operations
        for o in orders:
            if str(o.get("stat", "")).lower() != "complete":
                continue
            tag = str(o.get("tag") or o.get("ordModNo") or "").strip().upper()
            if tag.endswith("_X"):
                closed_tags.add(tag[:-2])

        # PASS 2: Map and structuralize original entries
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

        # PASS 3: Separate entries based on mapping definitions
        open_ledger = []
        closed_ledger = []

        for tag, details in raw_entries.items():
            if tag in closed_tags:
                closed_ledger.append(details)
            else:
                open_ledger.append(details)

        return open_ledger, closed_ledger

    except Exception as e:
        print(_pad_line_to_42(f"❌ Ledger Error {str(e)[:20]}", Fore.RED, Style.RESET_ALL))
        return [], []

# ----------------- CORE ENGINE PASS -----------------
async def exit_cycle():
    client = get_session()
    if not client:
        return

    from _sgnl import get_all_data
    data = get_all_data()
    entry_signal = str(data.get("entry", "")).upper().strip()
    index_ltp = float(data.get("price", 0))

    # Pull structural analysis mapping
    open_trades, closed_trades = analyze_and_map_all_orders(client)

    clear_screen()
    print(_pad_line_to_42("📋 ORDER MATRIX MAPPER (DRY RUN)", Fore.YELLOW + Style.BRIGHT, Style.RESET_ALL))
    print(_pad_line_to_42("=" * 42, Fore.YELLOW, Style.RESET_ALL))
    print(_pad_line_to_42(f"INDEX LTP : {index_ltp}", Fore.CYAN, Style.RESET_ALL))
    print(_pad_line_to_42(f"SIGNAL    : {entry_signal}", Fore.MAGENTA, Style.RESET_ALL))
    print(_pad_line_to_42("=" * 42, Fore.YELLOW, Style.RESET_ALL))

    # 1. RENDERING CLOSED TAGS SECTION
    print(_pad_line_to_42("🔒 CLOSED / MATCHED ORDERS:", Fore.WHITE + Style.BRIGHT, Style.RESET_ALL))
    if not closed_trades:
        print(_pad_line_to_42("  NONE RECORDED", Fore.LIGHTBLACK_EX, Style.RESET_ALL))
    for ct in closed_trades:
        print(_pad_line_to_42(f"  ✔️ {ct['tag']} @ {ct['entry_price']:.2f}", Fore.LIGHTBLACK_EX, Style.RESET_ALL))

    print(_pad_line_to_42("-" * 42, Fore.YELLOW, Style.RESET_ALL))

    # 2. RENDERING ACTIVE OPEN TAGS SECTION
    print(_pad_line_to_42("🔓 ACTIVE OPEN ORDERS:", Fore.WHITE + Style.BRIGHT, Style.RESET_ALL))
    if not open_trades:
        print(_pad_line_to_42("  NO OPEN POSITIONS", Fore.WHITE, Style.RESET_ALL))
        return

    for i, t in enumerate(open_trades):
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
                print(_pad_line_to_42(f"  [⚡] {t['tag']} TAIL TRIGGER MET", Fore.YELLOW, Style.RESET_ALL))

        elif t["txn_type"] == "S":
            pnl = (t["entry_price"] - option_ltp) * t["qty"]
            if pnl >= MIN_EXIT_PROFIT and entry_signal in ["BUY", "BULL"]:
                print(_pad_line_to_42(f"  [⚡] {t['tag']} TAIL TRIGGER MET", Fore.YELLOW, Style.RESET_ALL))

        color = Fore.GREEN if pnl >= 0 else Fore.RED
        print(_pad_line_to_42(
            f"  [{i}] {t['tag']} PnL:{int(pnl)}",
            color,
            Style.RESET_ALL
        ))

# ----------------- ENTRY POINT -----------------
async def main():
    await exit_cycle()

if __name__ == "__main__":
    asyncio.run(main())
