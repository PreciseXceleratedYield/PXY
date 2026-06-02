# _exit.py
import asyncio
import os
from datetime import datetime, time as dt_time
import pytz

from colorama import Fore, init, Style
from _sgnl import _pad_line_to_42
from _ltp import get_option_live_ltp  
from _clnt import get_session
from _pnl import log_closed_trade      
from _map import get_active_strategy_ledger  

# =====================================================================
# 🎛️ USER CONFIGURABLE STRATEGY MATRIX SETTINGS
# =====================================================================
MIN_EXIT_PROFIT = 500         # Rupee baseline target barrier threshold
STRATEGY_CUTOFF_TIME = "10:48" # 📊 ✅ Ignores all tags executed BEFORE this time
LOT_SIZE = 65

init(autoreset=True)

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def execute_exit(client, symbol, qty, txn_type, entry_tag):
    try:
        exit_tag = f"{entry_tag}_X"
        params = {
            "exchange_segment": "nse_fo", "product": "NRML", "price": "0",
            "order_type": "MKT", "quantity": str(qty), "validity": "DAY",
            "trading_symbol": symbol, "transaction_type": txn_type, "amo": "NO", "tag": exit_tag
        }
        res = client.place_order(**params)
        if res and str(res).strip():
            print(_pad_line_to_42(f"🏁 EXIT | {symbol[:15]} | {exit_tag}", Fore.MAGENTA + Style.BRIGHT, Style.RESET_ALL))
            return True
    except Exception as e:
        print(_pad_line_to_42(f"❌ Exit Error {str(e)[:20]}", Fore.RED, Style.RESET_ALL))
    return False

def force_global_account_flatten(client):
    try:
        pos_res = client.positions()
        positions = pos_res.get("data", [])
        if not isinstance(positions, list): return
        for p in positions:
            net_qty = float(p.get("net_qty", 0))
            if net_qty == 0: net_qty = float(p.get("flBuyQty", 0)) - float(p.get("flSellQty", 0))
            if abs(net_qty) <= 0: continue
            sym = str(p.get("trdSym", "")).upper()
            if "NIFTY" not in sym or "BANKNIFTY" in sym: continue
            txn = "S" if net_qty > 0 else "B"
            print(_pad_line_to_42(f"🚨 EOD EXIT {sym[:15]}", Fore.RED + Style.BRIGHT, Style.RESET_ALL))
            params = {
                "exchange_segment": "nse_fo", "product": "NRML", "price": "0",
                "order_type": "MKT", "quantity": str(int(abs(net_qty))), "validity": "DAY",
                "trading_symbol": sym, "transaction_type": txn, "amo": "NO", "tag": f"EOD_{datetime.now().strftime('%H%M%S')}"
            }
            client.place_order(**params)
    except Exception as e:
        print(_pad_line_to_42(f"❌ EOD FAIL {str(e)[:20]}", Fore.RED, Style.RESET_ALL))

async def exit_cycle():
    IST = pytz.timezone("Asia/Kolkata")
    now = datetime.now(IST).time()
    client = get_session()
    if not client: return

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

    if index_ltp == 0 or not entry_signal: return

    # ✅ TRANSMITS CONFIGURABLE TIME CUTOFF VALUE TO THE MATRIX PARSER MODULE
    df_ledger = get_active_strategy_ledger(client, diagnostic_mode=False, cutoff_time_str=STRATEGY_CUTOFF_TIME)

    clear_screen()
    print(_pad_line_to_42("📋 EXIT DASHBOARD", Fore.YELLOW + Style.BRIGHT, Style.RESET_ALL))
    print(_pad_line_to_42("=" * 42, Fore.YELLOW, Style.RESET_ALL))
    print(_pad_line_to_42(f"INDEX LTP : {index_ltp}", Fore.CYAN, Style.RESET_ALL))
    print(_pad_line_to_42(f"SIGNAL    : {entry_signal}", Fore.MAGENTA, Style.RESET_ALL))
    print(_pad_line_to_42(f"CUTOFF    : >= {STRATEGY_CUTOFF_TIME}", Fore.WHITE, Style.RESET_ALL))
    print(_pad_line_to_42("=" * 42, Fore.YELLOW, Style.RESET_ALL))

    if df_ledger.empty:
        print(_pad_line_to_42("NO ACTIVE STRATEGY TRADES", Fore.WHITE, Style.RESET_ALL))
        return

    for i, row in df_ledger.iterrows():
        t = row.to_dict()
        option_ltp = get_option_live_ltp(client=client, token_id=t["token"], ex_seg="nse_fo", fallback_price=t["entry_price"])
        pnl = 0.0 
        trigger_exit = False
        
        if t["txn_type"] == "B":
            pnl = (option_ltp - t["entry_price"]) * t["qty"]
            if pnl >= MIN_EXIT_PROFIT and entry_signal in ["SELL", "BEAR"]:
                trigger_exit = True
            if trigger_exit:
                if execute_exit(client, t["symbol"], t["qty"], "S", t["tag"]):
                    log_closed_trade(t["symbol"], t["qty"], t["tag"], t["token"], t["entry_price"], option_ltp, pnl, "B")
                    print(_pad_line_to_42(f"✅ EXITED LONG TAG: {t['tag']}", Fore.GREEN, Style.RESET_ALL))

        elif t["txn_type"] == "S":
            pnl = (t["entry_price"] - option_ltp) * t["qty"]
            if pnl >= MIN_EXIT_PROFIT and entry_signal in ["BUY", "BULL"]:
                trigger_exit = True
            if trigger_exit:
                if execute_exit(client, t["symbol"], t["qty"], "B", t["tag"]):
                    log_closed_trade(t["symbol"], t["qty"], t["tag"], t["token"], t["entry_price"], option_ltp, pnl, "S")
                    print(_pad_line_to_42(f"✅ EXITED SHORT TAG: {t['tag']}", Fore.GREEN, Style.RESET_ALL))

        if not trigger_exit:
            color = Fore.GREEN if pnl >= 0 else Fore.RED
            print(_pad_line_to_42(f"[{i}] {t['tag']} PnL:{int(pnl)}", color, Style.RESET_ALL))

async def main():
    try:
        await exit_cycle()
    except Exception as e:
        print(_pad_line_to_42(f"❌ Exit Failure: {str(e)[:22]}", Fore.RED, Style.RESET_ALL))

if __name__ == "__main__":
    asyncio.run(main())

