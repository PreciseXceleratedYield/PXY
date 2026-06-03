import os
import json
from datetime import datetime
import pandas as pd
from colorama import Fore, Style
from _sgnl import _pad_line_to_42

STATE_FILE = "trades.json"

def load_trades():
    if not os.path.exists(STATE_FILE): return {}
    try:
        with open(STATE_FILE, "r") as f: return json.load(f)
    except: return {}

def save_trades(trades):
    try:
        with open(STATE_FILE, "w") as f: json.dump(trades, f, indent=4)
    except: pass

def sync_and_build_dfs(client):
    """
    Downloads logs, structuralizes json, tracks trade loop pairings, 
    cleans anomalies, and maps to (df_open, df_done_and_dusted)
    """
    try:
        order_res = client.order_report()
        orders = order_res.get("data", []) if isinstance(order_res, dict) else order_res
        if not isinstance(orders, list):
            return pd.DataFrame(), pd.DataFrame()

        trades = load_trades()
        completed_exits = set()
        valid_broker_entries = set()

        # Step A: Isolate full execution loops via precise text slicing
        for o in orders:
            if str(o.get("stat", "")).strip().lower() != "complete": continue
            tag = str(o.get("tag", "")).strip().upper()
            if tag.endswith("_ENTRY_EXIT"):
                completed_exits.add(tag[:-5])  # Strip out exact "_EXIT" suffix
            if tag.endswith("_ENTRY"):
                valid_broker_entries.add(tag)

        # Step B: Log valid entry positions that don't exist locally yet
        for o in orders:
            if str(o.get("stat", "")).strip().lower() != "complete": continue
            tag = str(o.get("tag", "")).strip().upper()
            if not tag.endswith("_ENTRY"): continue

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

        # Step C: Pair completed positions instantly
        for tag in list(trades.keys()):
            if tag in completed_exits and trades[tag]["status"] == "OPEN":
                trades[tag]["status"] = "COMPLETED"
                trades[tag]["exit_tag"] = f"{tag}_EXIT"
                for o in orders:
                    if str(o.get("tag", "")).upper() == f"{tag}_EXIT":
                        trades[tag]["exit_price"] = float(o.get("avgPrc", 0))
                        break

        # Step D: Erase malformed, stuck or rejected data anomalies
        for tag in list(trades.keys()):
            if trades[tag]["status"] == "OPEN":
                if tag not in valid_broker_entries or (trades[tag]["entry_price"] == 0.0 and not trades[tag]["token"]):
                    print(_pad_line_to_42(f"🗑️ PURGED REJECTED: {tag}", Fore.RED + Style.BRIGHT, Style.RESET_ALL))
                    del trades[tag]

        save_trades(trades)

        if not trades:
            return pd.DataFrame(), pd.DataFrame()

        # Step E: Parse structural rows into clear pandas frames
        df_all = pd.DataFrame.from_dict(trades, orient="index")
        df_open = df_all[df_all["status"] == "OPEN"].copy()
        df_done = df_all[df_all["status"] == "COMPLETED"].copy()
        
        return df_open, df_done

    except Exception as e:
        print(_pad_line_to_42(f"⚠️ OMS Core Error: {str(e)[:22]}", Fore.RED, Style.RESET_ALL))
        return pd.DataFrame(), pd.DataFrame()

if __name__ == "__main__":
    from _clnt import get_session
    print("🧪 Running Independent OMS Module Data Test...")
    test_client = get_session()
    if test_client:
        df_open, df_done = sync_and_build_dfs(test_client)
        print(f"\n--- [DEBUG DF] OPEN ROWS ({len(df_open)}) ---")
        if not df_open.empty: print(df_open[["symbol", "qty", "entry_price", "current_signal"]])
        print(f"\n--- [DEBUG DF] DONE & DUSTED ROWS ({len(df_done)}) ---")
        if not df_done.empty: print(df_done[["symbol", "qty", "entry_price", "exit_price"]])
