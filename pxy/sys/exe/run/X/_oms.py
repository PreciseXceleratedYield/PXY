import os
import json
from datetime import datetime
import pandas as pd
from colorama import Fore, init, Style
from _sgnl import _pad_line_to_42

STATE_FILE = "trades.json"
init(autoreset=True)

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
    Downloads logs, prints raw data, maps tags globally, 
    and splits everything cleanly into (df_open, df_done_and_dusted)
    """
    try:
        order_res = client.order_report()
        
        # =====================================================================
        # 📡 TELEMETRY RAW DATA DIAGNOSTIC PRINTER
        # =====================================================================
        print(f"\n{Fore.CYAN}📡 [OMS TELEMETRY] RAW BROKER RESPONSE PAYLOAD:{Style.RESET_ALL}")
        print(json.dumps(order_res, indent=2) if isinstance(order_res, dict) else str(order_res))
        print(f"{Fore.CYAN}======================================================{Style.RESET_ALL}\n")

        orders = order_res.get("data", []) if isinstance(order_res, dict) else order_res
        if not isinstance(orders, list):
            orders = []

        trades = load_trades()
        completed_exits = set()

        # Step A: Scan for any completed or triggered exit loops
        for o in orders:
            tag = str(o.get("tag", "")).strip().upper()
            if tag.endswith("_ENTRY_EXIT") or tag.endswith("_EXIT"):
                # Cleanly isolate the parent entry identification tag
                parent_tag = tag.replace("_ENTRY_EXIT", "").replace("_EXIT", "")
                completed_exits.add(parent_tag)
                completed_exits.add(f"{parent_tag}_ENTRY")

        # Step B: Log and map every order into our state tracking system
        for o in orders:
            raw_tag = str(o.get("tag", "")).strip().upper()
            if not raw_tag: continue

            # Standardise tracking key to match parent strategy entry name
            tag = raw_tag.replace("_ENTRY_EXIT", "").replace("_EXIT", "")
            if not tag.endswith("_ENTRY") and f"{tag}_ENTRY" in trades:
                tag = f"{tag}_ENTRY"
            elif not tag.endswith("_ENTRY") and raw_tag.endswith("_ENTRY"):
                tag = raw_tag

            if tag not in trades:
                trades[tag] = {
                    "entry_tag": tag,
                    "exit_tag": "PENDING",
                    "symbol": str(o.get("trdSym", o.get("symbol", ""))).upper(),
                    "qty": int(float(o.get("fldQty", o.get("quantity", 0)))),
                    "entry_txn": str(o.get("trnsTp", o.get("transaction_type", ""))).upper(),
                    "entry_price": float(o.get("avgPrc", o.get("price", 0))),
                    "exit_price": 0.0,
                    "token": str(o.get("tok", o.get("token", ""))),
                    "status": "OPEN",
                    "current_signal": "NONE",
                    "opened_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }

        # Step C: Match completed exit states
        for tag in list(trades.keys()):
            clean_base_tag = tag.replace("_ENTRY", "")
            if tag in completed_exits or clean_base_tag in completed_exits:
                trades[tag]["status"] = "COMPLETED"
                trades[tag]["exit_tag"] = f"{clean_base_tag}_EXIT"
                
                # Fetch actual execution exit price from matching log row
                for o in orders:
                    o_tag = str(o.get("tag", "")).strip().upper()
                    if o_tag in [f"{clean_base_tag}_EXIT", f"{clean_base_tag}_ENTRY_EXIT"]:
                        trades[tag]["exit_price"] = float(o.get("avgPrc", o.get("price", 0)))
                        break

        save_trades(trades)

        if not trades:
            return pd.DataFrame(), pd.DataFrame()

        # Step D: Structure into clean open and closed DataFrames
        df_all = pd.DataFrame.from_dict(trades, orient="index")
        df_open = df_all[df_all["status"] == "OPEN"].copy()
        df_done = df_all[df_all["status"] == "COMPLETED"].copy()
        
        return df_open, df_done

    except Exception as e:
        print(_pad_line_to_42(f"⚠️ OMS Core Error: {str(e)[:22]}", Fore.RED, Style.RESET_ALL))
        return pd.DataFrame(), pd.DataFrame()

if __name__ == "__main__":
    from _clnt import get_session
    print("🧪 Running Expanded OMS Module Data Test...")
    test_client = get_session()
    if test_client:
        df_open, df_done = sync_and_build_dfs(test_client)
        print(f"\n--- [DEBUG DF] OPEN CANDIDATES ({len(df_open)}) ---")
        if not df_open.empty: print(df_open)
        print(f"\n--- [DEBUG DF] DONE & DUSTED ({len(df_done)}) ---")
        if not df_done.empty: print(df_done)

