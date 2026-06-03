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
    """
    Centralised OMS Gateway:
    1. Downloads logs and filters out historical trades executed before 10:00 AM IST.
    2. Synchronises open entries and settles finished bracket pairs using unique GuiOrdId timestamps.
    3. Calculates running unrealized PnL values natively with correct keyword arguments.
    Returns: (df_open_only, total_booked_pnl)
    """
    try:
        order_res = client.order_report()
        orders = order_res.get("data", []) if isinstance(order_res, dict) else order_res
        if not isinstance(orders, list):
            return pd.DataFrame(), 0.0

        # =====================================================================
        # ⏰ DYNAMIC TIME SHIELD: FILTER OUT HISTORICAL TRADES BEFORE 10:00 AM IST
        # =====================================================================
        tz_ist = pytz.timezone("Asia/Kolkata")
        now_ist = datetime.now(tz_ist)
        cutoff_datetime = tz_ist.localize(datetime.combine(now_ist.date(), time(10, 0, 0)))
        cutoff_epoch = int(cutoff_datetime.timestamp())

        executed_orders = []
        for o in orders:
            if str(o.get("stat", "")).strip().lower() != "complete": 
                continue
            order_time = int(float(o.get("boeSec", 0)))
            if order_time < cutoff_epoch:
                continue  # Bypasses all early morning trade clutter
            executed_orders.append(o)
        # =====================================================================

        trades = load_trades()
        completed_exits = set()
        valid_broker_entries = set()

        # Step A: Collect unique timestamp signatures for closures
        for o in executed_orders:
            gui_id = str(o.get("GuiOrdId", "")).strip().upper()
            if gui_id.endswith("_EXIT") or gui_id.endswith("_ENTRY_EXIT"):
                base_timestamp = gui_id.replace("_ENTRY_EXIT", "").replace("_EXIT", "")
                completed_exits.add(base_timestamp)
            if gui_id.endswith("_ENTRY"):
                valid_broker_entries.add(gui_id)

        # Step B: Log brand new individual strategy entry legs
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

        # Step C: Complete matching closed brackets
        for entry_tag in list(trades.keys()):
            base_timestamp = entry_tag.replace("_ENTRY", "")
            if base_timestamp in completed_exits and trades[entry_tag]["status"] == "OPEN":
                trades[entry_tag]["status"] = "COMPLETED"
                trades[entry_tag]["exit_tag"] = f"{base_timestamp}_EXIT"
                
                for o in executed_orders:
                    o_gui = str(o.get("GuiOrdId", "")).strip().upper()
                    if o_gui in [f"{base_timestamp}_EXIT", f"{base_timestamp}_ENTRY_EXIT"]:
                        trades[entry_tag]["exit_price"] = float(o.get("avgPrc", 0))
                        break

        # Step D: Auto-purge unexecuted or malformed data anomalies
        for entry_tag in list(trades.keys()):
            if trades[entry_tag]["status"] == "OPEN":
                if entry_tag not in valid_broker_entries or (trades[entry_tag]["entry_price"] == 0.0 and not trades[entry_tag]["token"]):
                    print(_pad_line_to_42(f"🗑️ PURGED REJECTED: {entry_tag}", Fore.RED + Style.BRIGHT, Style.RESET_ALL))
                    del trades[entry_tag]

        save_trades(trades)

        if not trades:
            return pd.DataFrame(), 0.0

        df_all = pd.DataFrame.from_dict(trades, orient="index")
        if "status" not in df_all.columns:
            return pd.DataFrame(), 0.0

        # Step E: Calculate realized booked profits from completed rows
        df_done = df_all[df_all["status"] == "COMPLETED"].copy()
        booked_pnl = 0.0
        if not df_done.empty:
            for idx, row in df_done.iterrows():
                qty = row["qty"]
                e_prc = row["entry_price"]
                x_prc = row["exit_price"]
                booked_pnl += (x_prc - e_prc) * qty if row["entry_txn"] == "B" else (e_prc - x_prc) * qty

        # Step F: Isolate OPEN contracts and append pre-calculated live profits
        df_open = df_all[df_all["status"] == "OPEN"].copy()
        if not df_open.empty:
            unrealized_pnl_list = []
            live_ltp_list = []
            
            for idx, row in df_open.iterrows():
                raw_token = row["token"] if "token" in row else row["tok"]
                if isinstance(raw_token, pd.Series):
                    raw_token = raw_token.iloc if not raw_token.empty else ""
                token = str(raw_token).strip()

                entry_price = float(row["entry_price"])
                qty = int(row["qty"])
                entry_txn = str(row["entry_txn"]).upper()

                # FIXED KEYWORD ARGUMENT: fallback_price used precisely as declared in _ltp.py
                try:
                    live_ltp = float(get_option_live_ltp(client, token, "nse_fo", fallback_price=entry_price))
                except Exception as e:
                    print(_pad_line_to_42(f"⚠️ OMS Error: get_option_live_ltp execution failed.", Fore.RED, Style.RESET_ALL))
                    live_ltp = entry_price

                live_ltp_list.append(live_ltp)

                pnl = (live_ltp - entry_price) * qty if entry_txn == "B" else (entry_price - live_ltp) * qty
                unrealized_pnl_list.append(pnl)

            df_open["live_ltp"] = live_ltp_list
            df_open["unrealized_pnl"] = unrealized_pnl_list

        return df_open, booked_pnl

    except Exception as e:
        print(_pad_line_to_42(f"⚠️ OMS Core Error: {str(e)[:22]}", Fore.RED, Style.RESET_ALL))
        return pd.DataFrame(), 0.0

if __name__ == "__main__":
    from _clnt import get_session
    print("🧪 Testing Advanced Filtered OMS Output Pipeline...")
    test_client = get_session()
    if test_client:
        df_open_only, session_pnl = get_open_candidates_and_pnl(test_client)
        print(f"\n💰 REALIZED CLOSED SESSION PNL: Rs.{session_pnl:.2f}")
        print(f"\n--- [DEBUG DF] HANDING OVER OPEN TRADES ONLY ({len(df_open_only)}) ---")
        if not df_open_only.empty: 
            print(df_open_only[["symbol", "qty", "entry_price", "live_ltp", "unrealized_pnl", "current_signal"]])


