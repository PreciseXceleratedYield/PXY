import os
import json
from datetime import datetime, time
import pytz
import pandas as pd
from colorama import Fore, init, Style
from _sgnl import _pad_line_to_42
from _ltp import get_option_live_ltp

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

def get_open_candidates_and_pnl(client):
    try:
        order_res = client.order_report()
        orders = order_res.get("data", []) if isinstance(order_res, dict) else order_res
        if not isinstance(orders, list): return pd.DataFrame(), 0.0

        # =====================================================================
        # ⏰ TIME SHIELD: BLOCK ALL CLUTTER EXECUTED BEFORE 10:00 AM IST TODAY
        # =====================================================================
        tz_ist = pytz.timezone("Asia/Kolkata")
        now_ist = datetime.now(tz_ist)
        cutoff_datetime = tz_ist.localize(datetime.combine(now_ist.date(), time(10, 0, 0)))
        cutoff_epoch = int(cutoff_datetime.timestamp())

        executed_orders = []
        for o in orders:
            if str(o.get("stat", "")).strip().lower() != "complete": continue
            if int(float(o.get("boeSec", 0))) < cutoff_epoch: continue
            executed_orders.append(o)

        trades = load_trades()
        completed_exits = set()
        valid_broker_entries = set()

        for o in executed_orders:
            gui_id = str(o.get("GuiOrdId", "")).strip().upper()
            if gui_id.endswith("_EXIT") or gui_id.endswith("_ENTRY_EXIT"):
                completed_exits.add(gui_id.replace("_ENTRY_EXIT", "").replace("_EXIT", ""))
            if gui_id.endswith("_ENTRY"): valid_broker_entries.add(gui_id)

        for o in executed_orders:
            gui_id = str(o.get("GuiOrdId", "")).strip().upper()
            if not gui_id.endswith("_ENTRY"): continue
            if gui_id not in trades:
                trades[gui_id] = {
                    "entry_tag": gui_id, "exit_tag": "PENDING", "symbol": str(o.get("trdSym", "")).upper(),
                    "qty": int(float(o.get("fldQty", 0))), "entry_txn": str(o.get("trnsTp", "")).upper(),
                    "entry_price": float(o.get("avgPrc", 0)), "exit_price": 0.0, "token": str(o.get("tok", "")),
                    "status": "OPEN", "current_signal": "NONE", "opened_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }

        for entry_tag in list(trades.keys()):
            base_ts = entry_tag.replace("_ENTRY", "")
            if base_ts in completed_exits and trades[entry_tag]["status"] == "OPEN":
                trades[entry_tag]["status"] = "COMPLETED"
                trades[entry_tag]["exit_tag"] = f"{base_ts}_EXIT"
                for o in executed_orders:
                    if str(o.get("GuiOrdId", "")).strip().upper() in [f"{base_ts}_EXIT", f"{base_ts}_ENTRY_EXIT"]:
                        trades[entry_tag]["exit_price"] = float(o.get("avgPrc", 0))
                        break

        for entry_tag in list(trades.keys()):
            if trades[entry_tag]["status"] == "OPEN":
                if entry_tag not in valid_broker_entries or (trades[entry_tag]["entry_price"] == 0.0 and not trades[entry_tag]["token"]):
                    del trades[entry_tag]

        save_trades(trades)
        if not trades: return pd.DataFrame(), 0.0

        df_all = pd.DataFrame.from_dict(trades, orient="index")
        if "status" not in df_all.columns: return pd.DataFrame(), 0.0

        # Calculate Realized Booked Metrics
        df_done = df_all[df_all["status"] == "COMPLETED"].copy()
        booked_pnl = 0.0
        if not df_done.empty:
            for _, r in df_done.iterrows():
                booked_pnl += (r["exit_price"] - r["entry_price"]) * r["qty"] if r["entry_txn"] == "B" else (r["entry_price"] - r["exit_price"]) * r["qty"]

        # Isolate open rows and calculate live pricing columns
        df_open = df_all[df_all["status"] == "OPEN"].copy()
        if not df_open.empty:
            unrealized_pnl_list, live_ltp_list = [], []
            for _, r in df_open.iterrows():
                token = str(r["token"] if "token" in r else r["tok"]).strip()
                ep, qty, txn = float(r["entry_price"]), int(r["qty"]), str(r["entry_txn"])
                try:
                    live_ltp = float(get_option_live_ltp(client, token, "nse_fo", fallback_price=ep))
                except:
                    live_ltp = ep
                live_ltp_list.append(live_ltp)
                unrealized_pnl_list.append((live_ltp - ep) * qty if txn == "B" else (ep - live_ltp) * qty)
            
            df_open["live_ltp"] = live_ltp_list
            df_open["unrealized_pnl"] = unrealized_pnl_list

        return df_open, booked_pnl
    except Exception as e:
        print(_pad_line_to_42(f"⚠️ OMS Error: {str(e)[:22]}", Fore.RED, Style.RESET_ALL))
        return pd.DataFrame(), 0.0


