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
    Downloads logs, tracks trades as individual positions based strictly 
    on matching timestamp prefixes inside GuiOrdId, and builds DataFrames.
    """
    try:
        order_res = client.order_report()
        orders = order_res.get("data", []) if isinstance(order_res, dict) else order_res
        if not isinstance(orders, list):
            return pd.DataFrame(), pd.DataFrame()

        # Isolate complete executions
        executed_orders = [o for o in orders if str(o.get("stat", "")).strip().lower() == "complete"]
        
        trades = load_trades()
        completed_exits = set()
        valid_broker_entries = set()

        # Step A: Collect all exit timestamps in the broker logs (e.g., '0603094435' from '0603094435_EXIT')
        for o in executed_orders:
            gui_id = str(o.get("GuiOrdId", "")).strip().upper()
            if gui_id.endswith("_EXIT") or gui_id.endswith("_ENTRY_EXIT"):
                base_timestamp = gui_id.replace("_ENTRY_EXIT", "").replace("_EXIT", "")
                completed_exits.add(base_timestamp)
            if gui_id.endswith("_ENTRY"):
                valid_broker_entries.add(gui_id)

        # Step B: Log each unique entry into your local JSON tracking file
        for o in executed_orders:
            gui_id = str(o.get("GuiOrdId", "")).strip().upper()
            if not gui_id.endswith("_ENTRY"): continue

            if gui_id not in trades:
                trades[gui_id] = {
                    "entry_tag": gui_id,
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

        # Step C: Match completed exit loops strictly by matching timestamp bases
        for entry_tag in list(trades.keys()):
            base_timestamp = entry_tag.replace("_ENTRY", "")
            
            # If an exit tag sharing this unique timestamp prefix exists in broker logs, close it
            if base_timestamp in completed_exits and trades[entry_tag]["status"] == "OPEN":
                trades[entry_tag]["status"] = "COMPLETED"
                trades[entry_tag]["exit_tag"] = f"{base_timestamp}_EXIT"
                
                # Extract the actual execution exit price from that matching exit leg row
                for o in executed_orders:
                    o_gui = str(o.get("GuiOrdId", "")).strip().upper()
                    if o_gui in [f"{base_timestamp}_EXIT", f"{base_timestamp}_ENTRY_EXIT"]:
                        trades[entry_tag]["exit_price"] = float(o.get("avgPrc", 0))
                        break

        # Step D: Clear rejected/ghost entry data structures
        for entry_tag in list(trades.keys()):
            if trades[entry_tag]["status"] == "OPEN":
                if entry_tag not in valid_broker_entries or (trades[entry_tag]["entry_price"] == 0.0 and not trades[entry_tag]["token"]):
                    print(_pad_line_to_42(f"🗑️ PURGED REJECTED: {entry_tag}", Fore.RED + Style.BRIGHT, Style.RESET_ALL))
                    del trades[entry_tag]

        save_trades(trades)

        if not trades:
            return pd.DataFrame(), pd.DataFrame()

        # Step E: Construct structured pandas sheets for analysis
        df_all = pd.DataFrame.from_dict(trades, orient="index")
        df_open = df_all[df_all["status"] == "OPEN"].copy()
        df_done = df_all[df_all["status"] == "COMPLETED"].copy()
        
        return df_open, df_done

    except Exception as e:
        print(_pad_line_to_42(f"⚠️ OMS Core Error: {str(e)[:22]}", Fore.RED, Style.RESET_ALL))
        return pd.DataFrame(), pd.DataFrame()

if __name__ == "__main__":
    from _clnt import get_session
    print("🧪 Running Fixed Kotak OMS Data Test...")
    test_client = get_session()
    if test_client:
        df_open, df_done = sync_and_build_dfs(test_client)
        print(f"\n--- [DEBUG] EXIT CANDIDATES (OPEN) Rows: {len(df_open)} ---")
        if not df_open.empty: print(df_open[["symbol", "qty", "entry_price", "current_signal"]])
        print(f"\n--- [DEBUG] DONE AND DUSTED Rows: {len(df_done)} ---")
        if not df_done.empty: print(df_done[["symbol", "qty", "entry_price", "exit_price"]])

