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
MIN_EXIT_PROFIT = 350

init(autoreset=True)


# ---------------- SCREEN ----------------
def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')


# ---------------- ORDER LEDGER ----------------
def reconstruct_fifo_ledger_from_orders(client):
    """
    Builds an independent position ledger grouped strictly by unique Entry Tags.
    Guarantees strict isolation of open tags regardless of broker API sorting.
    """
    try:
        order_res = client.order_report()  
        orders = order_res.get("data", []) if isinstance(order_res, dict) else order_res
        if not isinstance(orders, list):
            return []

        raw_entries = {}
        closed_tags = set()

        # PASS 1: Sweep the entire order book strictly to find ALL completed exit tokens
        for o in orders:
            if str(o.get("stat", "")).lower() != "complete":
                continue
            tag = str(o.get("tag") or o.get("ordModNo") or "").strip().upper()
            if tag.endswith("_X"):
                closed_tags.add(tag[:-2])  # Isolate and log the original parent tag

        # PASS 2: Collect valid entry frameworks that are NOT confirmed in the closed set
        for o in orders:
            if str(o.get("stat", "")).lower() != "complete":
                continue
            tag = str(o.get("tag") or o.get("ordModNo") or "").strip().upper()
            
            if not (tag.endswith("_BUY") or tag.endswith("_SELL")):
                continue
                
            if tag in closed_tags:
                continue

            qty = int(float(o.get("fldQty", 0)))
            if qty <= 0:
                continue

            raw_entries[tag] = {
                "symbol": o.get("trdSym", ""),
                "txn_type": str(o.get("trnsTp", "")).upper().strip(),  # "B" (Buy) or "S" (Sell)
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

    # Fetch the cleaned ledger listing ONLY open tags
    ledger = reconstruct_fifo_ledger_from_orders(client)

    clear_screen()
    print(_pad_line_to_42("📋 EXIT DASHBOARD", Fore.YELLOW + Style.BRIGHT, Style.RESET_ALL))
    print(_pad_line_to_42("=" * 42, Fore.YELLOW, Style.RESET_ALL))
    print(_pad_line_to_42(f"INDEX LTP : {index_ltp}", Fore.CYAN, Style.RESET_ALL))
    print(_pad_line_to_42(f"SIGNAL    : {entry_signal}", Fore.MAGENTA, Style.RESET_ALL))
    print(_pad_line_to_42("=" * 42, Fore.YELLOW, Style.RESET_ALL))

    if not ledger:
        print(_pad_line_to_42("NO ACTIVE TRADES", Fore.WHITE, Style.RESET_ALL))
        return

    # Display and track all isolated open tag records sequentially
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
                    continue  

        # Short positions processing pipeline (-65 Qty)
        elif t["txn_type"] == "S":
            pnl = (t["entry_price"] - option_ltp) * t["qty"]
            
            # STRICT AND LOGIC: Must be profitable AND trend must reverse to exit
            if pnl >= MIN_EXIT_PROFIT and entry_signal in ["BUY", "BULL"]:
                trigger_exit = True

            if trigger_exit:
                if execute_exit(client, t["symbol"], t["qty"], "B", t["tag"]):
                    log_closed_trade(t["symbol"], t["qty"], t["tag"], t["token"], t["entry_price"], option_ltp, pnl, "S")
                    continue  

        color = Fore.GREEN if pnl >= 0 else Fore.RED
        print(_pad_line_to_42(
            f"[{i}] {t['tag']} PnL:{int(pnl)}",
            color,
            Style.RESET_ALL
        ))


# ---------------- SINGLE EXECUTION STRUCTURING ----------------
async def main():
    try:
        # Runs exactly once and exits cleanly
        await exit_cycle()
    except Exception as e:
        print(_pad_line_to_42(f"❌ Exit Failure: {str(e)[:22]}", Fore.RED, Style.RESET_ALL))

if __name__ == "__main__":
    asyncio.run(main())

