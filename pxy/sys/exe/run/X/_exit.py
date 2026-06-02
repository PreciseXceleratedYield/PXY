# _exit.py
import asyncio
import os
from datetime import datetime, time as dt_time
import pytz

from colorama import Fore, init, Style
from _sgnl import _pad_line_to_42
from _ltp import get_option_live_ltp  # Uses your 5-tier fallback script
from _clnt import get_session
from _pnl import log_closed_trade      # Imported isolated function directly

LOT_SIZE = 65
MIN_EXIT_PROFIT = 500

init(autoreset=True)


# ---------------- SCREEN ----------------
def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')


# ---------------- ORDER LEDGER ----------------
def reconstruct_fifo_ledger_from_orders(client):
    """
    Builds an independent position ledger grouped strictly by unique Entry Tags.
    Filters out closed tags completely using symbol volume netting and exit tags.
    """
    try:
        order_res = client.order_report()  
        orders = order_res.get("data", []) if isinstance(order_res, dict) else order_res
        if not isinstance(orders, list):
            return []

        # STAGE 1: SYMBOL QUANTITY VOLUME NETTING (Catches Manual App Exits)
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

        # STAGE 2: PARSING AND CLASSIFYING STRATEGY TAGS
        raw_entries = {}
        closed_tags = set()

        # Step 2A: Collect entry tags closed via standard automated '_X' suffixes
        for o in orders:
            status = str(o.get("stat", "")).strip().lower()
            if status != "complete": 
                continue
            tag = str(o.get("tag") or o.get("ordModNo") or "").strip().upper()
            if tag.endswith("_X"):
                parent_tag = tag[:-2]
                closed_tags.add(parent_tag)

        # Step 2B: Compile active strategy entry nodes, dropping closed ones
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

            # If volume netting is 0 OR tag match confirms closed, filter it out completely
            if symbol_net_qty.get(sym, 0) == 0 or tag in closed_tags:
                continue

            raw_entries[tag] = {
                "symbol": sym,
                "txn_type": str(o.get("trnsTp", "")).upper().strip(),
                "entry_price": float(o.get("avgPrc", 0)),
                "qty": qty,
                "tag": tag,
                "token": o.get("tok")  
            }

        return list(raw_entries.values())

    except Exception as e:
        print(_pad_line_to_42(f"❌ Ledger Error {str(e)[:20]}", Fore.RED, Style.RESET_ALL))
        return []


# ---------------- EXIT ORDER ----------------
def execute_exit(client, symbol, qty, txn_type, entry_tag):
    """ Executes real market orders to close the active option positions. """
    try:
        exit_tag = f"{entry_tag}_X"
        params = {
            "exchange_segment": "nse_fo",
            "product": "NRML",
            "price": "0",
            "order_type": "MKT",
            "quantity": str(qty),
            "validity": "DAY",
            "trading_symbol": symbol,
            "transaction_type": txn_type,
            "amo": "NO",
            "tag": exit_tag
        }

        res = client.place_order(**params)

        if res and str(res).strip():
            print(
                _pad_line_to_42(
                    f"🏁 EXIT | {symbol[:15]} | {exit_tag}",
                    Fore.MAGENTA + Style.BRIGHT,
                    Style.RESET_ALL
                )
            )
            return True

    except Exception as e:
        print(_pad_line_to_42(f"❌ Exit Error {str(e)[:20]}", Fore.RED, Style.RESET_ALL))

    return False


# ---------------- FORCE FLATTEN ----------------
def force_global_account_flatten(client):
    try:
        pos_res = client.positions()
        positions = pos_res.get("data", [])

        if not isinstance(positions, list):
            return

        for p in positions:
            net_qty = float(p.get("net_qty", 0))
            if net_qty == 0:
                net_qty = float(p.get("flBuyQty", 0)) - float(p.get("flSellQty", 0))

            if abs(net_qty) <= 0:
                continue

            sym = str(p.get("trdSym", "")).upper()
            if "NIFTY" not in sym or "BANKNIFTY" in sym:
                continue

            txn = "S" if net_qty > 0 else "B"

            print(_pad_line_to_42(
                f"🚨 EOD EXIT {sym[:15]}",
                Fore.RED + Style.BRIGHT,
                Style.RESET_ALL
            ))

            params = {
                "exchange_segment": "nse_fo",
                "product": "NRML",
                "price": "0",
                "order_type": "MKT",
                "quantity": str(int(abs(net_qty))),
                "validity": "DAY",
                "trading_symbol": sym,
                "transaction_type": txn,
                "amo": "NO",
                "tag": f"EOD_{datetime.now().strftime('%H%M%S')}"
            }
            client.place_order(**params)

    except Exception as e:
        print(_pad_line_to_42(f"❌ EOD FAIL {str(e)[:20]}", Fore.RED, Style.RESET_ALL))


# ---------------- EXIT ENGINE ----------------
async def exit_cycle():
    IST = pytz.timezone("Asia/Kolkata")
    now = datetime.now(IST).time()

    client = get_session()
    if not client:
        return

    if dt_time(15, 20) <= now < dt_time(15, 26):
        clear_screen()
        print(_pad_line_to_42("⏳ EOD FORCE FLATTEN", Fore.RED + Style.BRIGHT, Style.RESET_ALL))
        force_global_account_flatten(client)
        return

    if (dt_time(9, 14) <= now < dt_time(9, 16)) or (dt_time(15, 25) <= now < dt_time(15, 31)):
        clear_screen()
        print(_pad_line_to_42("⏳ SYSTEM BUFFER", Fore.YELLOW, Style.RESET_ALL))
        return

    from _sgnl import get_all_data

    data = get_all_data()
    entry_signal = str(data.get("entry", "")).upper().strip()
    index_ltp = float(data.get("price", 0))

    if index_ltp == 0 or not entry_signal:
        return

    # Fetch ledger listing ONLY live unmatched open trades (Closed items filtered out)
    ledger = reconstruct_fifo_ledger_from_orders(client)

    clear_screen()
    print(_pad_line_to_42("📋 EXIT DASHBOARD", Fore.YELLOW + Style.BRIGHT, Style.RESET_ALL))
    print(_pad_line_to_42("=" * 42, Fore.YELLOW, Style.RESET_ALL))
    print(_pad_line_to_42(f"INDEX LTP : {index_ltp}", Fore.CYAN, Style.RESET_ALL))
    print(_pad_line_to_42(f"SIGNAL    : {entry_signal}", Fore.MAGENTA, Style.RESET_ALL))
    print(_pad_line_to_42("=" * 42, Fore.YELLOW, Style.RESET_ALL))

    if not ledger:
        print(_pad_line_to_42("NO ACTIVE STRATEGY TRADES", Fore.WHITE, Style.RESET_ALL))
        return

    # Process live strategic open orders
    for i, t in enumerate(ledger):
        option_ltp = get_option_live_ltp(
            client=client,
            token_id=t["token"],
            ex_seg="nse_fo",
            fallback_price=t["entry_price"]
        )

        pnl = 0.0 
        trigger_exit = False
        
        # Long positions processing pipeline (+65 Qty)
        if t["txn_type"] == "B":
            pnl = (option_ltp - t["entry_price"]) * t["qty"]
            
            # STRICT AND LOGIC: Must be profitable AND trend must reverse to exit
            if pnl >= MIN_EXIT_PROFIT and entry_signal in ["SELL", "BEAR"]:
                trigger_exit = True

            if trigger_exit:
                if execute_exit(client, t["symbol"], t["qty"], "S", t["tag"]):
                    log_closed_trade(t["symbol"], t["qty"], t["tag"], t["token"], t["entry_price"], option_ltp, pnl, "B")
                    print(_pad_line_to_42(f"✅ EXITED LONG TAG: {t['tag']}", Fore.GREEN, Style.RESET_ALL))

        # Short positions processing pipeline (-65 Qty)
        elif t["txn_type"] == "S":
            pnl = (t["entry_price"] - option_ltp) * t["qty"]
            
            # STRICT AND LOGIC: Must be profitable AND trend must reverse to exit
            if pnl >= MIN_EXIT_PROFIT and entry_signal in ["BUY", "BULL"]:
                trigger_exit = True

            if trigger_exit:
                if execute_exit(client, t["symbol"], t["qty"], "B", t["tag"]):
                    log_closed_trade(t["symbol"], t["qty"], t["tag"], t["token"], t["entry_price"], option_ltp, pnl, "S")
                    print(_pad_line_to_42(f"✅ EXITED SHORT TAG: {t['tag']}", Fore.GREEN, Style.RESET_ALL))

        if not trigger_exit:
            color = Fore.GREEN if pnl >= 0 else Fore.RED
            print(_pad_line_to_42(
                f"[{i}] {t['tag']} PnL:{int(pnl)}",
                color,
                Style.RESET_ALL
            ))


# ---------------- SINGLE EXECUTION STRUCTURING ----------------
async def main():
    try:
        # Runs exactly once per execution trigger pass and terminates cleanly
        await exit_cycle()
    except Exception as e:
        print(_pad_line_to_42(f"❌ Exit Failure: {str(e)[:22]}", Fore.RED, Style.RESET_ALL))

if __name__ == "__main__":
    asyncio.run(main())

